<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { DatasetInfo } from '~/composables/useDatasetInfo'
import type { DatasetAgreement } from '~/types'
import { useLocalStorage } from '@vueuse/core'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  datasetId: number
}>()

const { fetchAgreement } = useDatasets()
const { fetchDatasetInfo } = useDatasetInfo()

const headers = ref<string[]>([])
const result = ref<DatasetAgreement | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// The columns picked are remembered per dataset, in this browser
const stored = useLocalStorage<string[]>(workspaceStorageKey(`maestro:dataset-agreement-${props.datasetId}`), [])

// A column removed from the file drops out of the selection
const selected = computed({
  get: () => stored.value.filter(column => headers.value.includes(column)),
  set: (columns: string[]) => {
    stored.value = columns
  },
})

// Only the latest request may land: picking columns quickly must not show an older answer
let lastRequest = 0

async function load() {
  const request = ++lastRequest
  const columns = selected.value
  if (columns.length < 2) {
    result.value = null
    error.value = null
    loading.value = false
    return
  }

  loading.value = true
  error.value = null
  try {
    const data = await fetchAgreement(props.datasetId, columns)
    if (request === lastRequest)
      result.value = data
  }
  catch (e) {
    if (request !== lastRequest)
      return
    result.value = null
    error.value = apiErrorMessage(e) ?? 'Couldn’t compute the agreement'
  }
  finally {
    if (request === lastRequest)
      loading.value = false
  }
}

onMounted(async () => {
  const info = await fetchDatasetInfo(props.datasetId)
  if (info.success && info.data)
    headers.value = (info.data as DatasetInfo).headers
  else
    error.value = 'Couldn’t read the columns of the dataset'
})

// Runs once the columns are known, then on each change of the selection
watch([headers, () => selected.value.join('\u0000')], load)

const isNumeric = computed(() => result.value?.value_type === 'numeric')

function formatPercent(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${Math.round(value * 100)}%`
}

// Exact agreement reads as a share; the other metrics are coefficients
function formatPairMetric(key: string, value: number | null) {
  return key === 'accuracy' ? formatPercent(value) : formatMetric(value)
}

// Krippendorff's thresholds: below 0.667 the ratings are too inconsistent to build on
const ALPHA_THRESHOLDS = 'At least 0.80: reliable. From 0.667 to 0.80: tentative conclusions only. Below 0.667: unreliable.'

const alphaVerdict = computed(() => {
  const alpha = result.value?.overall.alpha.value
  if (alpha === null || alpha === undefined)
    return null
  if (alpha >= 0.8)
    return 'Reliable'
  return alpha >= 0.667 ? 'Tentative' : 'Unreliable'
})

const hasMissing = computed(() => result.value?.columns.some(c => c.n_missing > 0) ?? false)
</script>

<template>
  <div class="flex flex-col gap-4 overflow-y-auto">
    <section class="rounded-lg border border-default">
      <div role="group" aria-labelledby="agreement-columns" class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        <div class="min-w-0">
          <p id="agreement-columns" class="text-sm text-highlighted">
            Columns
          </p>
          <p class="text-xs text-muted text-pretty">
            Pick the columns that rate the same rows, like two annotators. Leave out a column computed from the others, such as their average: it inflates the agreement.
          </p>
        </div>
        <USelectMenu
          v-model="selected"
          multiple
          :items="headers"
          :search-input="{ placeholder: 'Search columns…' }"
          placeholder="Select columns"
          :ui="{ value: 'font-mono text-xs' }"
          size="sm"
          class="w-full sm:w-80 shrink-0"
        />
      </div>
    </section>

    <UAlert
      v-if="error"
      color="error"
      variant="subtle"
      icon="i-ph-warning-circle-bold"
      title="Couldn’t compute the agreement"
      :description="error"
    />

    <USkeleton v-else-if="!headers.length" class="h-20 w-full" />

    <BaseEmptyState
      v-else-if="selected.length < 2"
      icon="i-ph-users-three-bold"
      title="Compare at least two columns"
      message="Select the columns that hold each annotator’s score or label to see how much they agree."
    />

    <div v-else-if="!result" class="flex flex-col gap-3">
      <USkeleton class="h-20 w-full" />
      <USkeleton class="h-40 w-full" />
    </div>

    <!-- The previous numbers stay, dimmed, while a new selection is computed -->
    <div
      v-else
      class="flex flex-col gap-4 transition-opacity duration-150"
      :class="loading && 'opacity-60'"
      :aria-busy="loading"
    >
      <UAlert
        v-for="warning in result.warnings"
        :key="warning"
        color="warning"
        variant="subtle"
        icon="i-ph-warning-bold"
        :title="warning"
      />

      <dl class="grid gap-px overflow-hidden rounded-lg border border-default bg-border sm:grid-cols-3">
        <div class="bg-default px-4 py-3">
          <dt class="text-xs text-muted">
            <UTooltip :text="`Agreement of all the columns together, corrected for chance, with missing ratings allowed. ${ALPHA_THRESHOLDS}`">
              <button type="button" class="cursor-help rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted">
                Krippendorff’s α
              </button>
            </UTooltip>
          </dt>
          <dd class="mt-1 flex items-baseline gap-2">
            <template v-if="result.overall.alpha.value !== null">
              <span class="text-2xl font-semibold tabular-nums text-highlighted">{{ formatMetric(result.overall.alpha.value) }}</span>
              <span class="text-xs text-muted">{{ alphaVerdict }}</span>
            </template>
            <UTooltip v-else :text="result.overall.alpha.undefined_reason ?? 'Undefined'">
              <span tabindex="0" class="text-2xl text-muted rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted">—<span class="sr-only">{{ result.overall.alpha.undefined_reason ?? 'Undefined' }}</span></span>
            </UTooltip>
          </dd>
        </div>
        <div class="bg-default px-4 py-3">
          <dt class="text-xs text-muted">
            Unanimous rows
          </dt>
          <dd class="mt-1 text-2xl font-semibold tabular-nums text-highlighted">
            {{ formatPercent(result.overall.unanimous) }}
          </dd>
        </div>
        <div class="bg-default px-4 py-3">
          <dt class="text-xs text-muted">
            Rows compared
          </dt>
          <dd class="mt-1 flex items-baseline gap-2">
            <span class="text-2xl font-semibold tabular-nums text-highlighted">{{ result.overall.n_items.toLocaleString('en-US') }}</span>
            <span class="text-xs text-muted tabular-nums">of {{ result.n_rows.toLocaleString('en-US') }} · {{ isNumeric ? 'numeric scores' : 'labels' }}</span>
          </dd>
        </div>
      </dl>

      <BaseSection title="Columns">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-muted border-b border-default">
                <th class="px-4 py-2 font-medium">
                  Column
                </th>
                <th class="px-4 py-2 font-medium text-right">
                  Rated
                </th>
                <th v-if="hasMissing" class="px-4 py-2 font-medium text-right">
                  Blank
                </th>
                <th v-if="isNumeric" class="px-4 py-2 font-medium text-right">
                  <UTooltip text="A column whose mean sits apart from the others is stricter or more lenient: they disagree even when they rank rows the same way.">
                    <button type="button" class="cursor-help rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted">
                      Mean
                    </button>
                  </UTooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="column in result.columns" :key="column.column" class="border-b border-muted last:border-0">
                <td class="px-4 py-1.5 font-mono text-xs text-highlighted">
                  {{ column.column }}
                </td>
                <td class="px-4 py-1.5 text-right tabular-nums">
                  {{ column.n.toLocaleString('en-US') }}
                </td>
                <td v-if="hasMissing" class="px-4 py-1.5 text-right tabular-nums" :class="column.n_missing ? 'text-warning' : 'text-muted'">
                  {{ column.n_missing.toLocaleString('en-US') }}
                </td>
                <td v-if="isNumeric" class="px-4 py-1.5 text-right tabular-nums">
                  {{ formatMetric(column.mean) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseSection>

      <BaseSection title="Pairs">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs text-muted border-b border-default">
                <th class="px-4 py-2 font-medium">
                  Pair
                </th>
                <th class="px-4 py-2 font-medium text-right">
                  Rows
                </th>
                <th v-for="m in result.metrics" :key="m.key" class="px-4 py-2 font-medium text-right whitespace-nowrap">
                  <UTooltip :text="m.description">
                    <button type="button" class="cursor-help rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted">
                      {{ m.label }}
                    </button>
                  </UTooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="pair in result.pairs" :key="`${pair.a}-${pair.b}`" class="border-b border-muted last:border-0">
                <td class="px-4 py-1.5 font-mono text-xs text-highlighted whitespace-nowrap">
                  {{ pair.a }} <span class="text-dimmed">↔</span> {{ pair.b }}
                </td>
                <td class="px-4 py-1.5 text-right tabular-nums">
                  {{ pair.n.toLocaleString('en-US') }}
                </td>
                <td v-for="m in result.metrics" :key="m.key" class="px-4 py-1.5 text-right tabular-nums whitespace-nowrap">
                  <template v-if="pair.metrics[m.key]?.value !== null && pair.metrics[m.key]?.value !== undefined">
                    {{ formatPairMetric(m.key, pair.metrics[m.key]!.value) }}
                  </template>
                  <UTooltip v-else :text="pair.metrics[m.key]?.undefined_reason ?? 'Undefined'">
                    <span tabindex="0" class="text-muted rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted">—<span class="sr-only">{{ pair.metrics[m.key]?.undefined_reason ?? 'Undefined' }}</span></span>
                  </UTooltip>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseSection>

      <p class="text-xs text-muted">
        Computed from the saved file.
      </p>
    </div>
  </div>
</template>
