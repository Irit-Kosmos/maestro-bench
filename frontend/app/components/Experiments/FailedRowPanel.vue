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
import type { ExecutionRow, FailureGroup } from '~/types'

// A failed row of an execution in full, to see what the agents were sent and
// what stopped them. Steps through the other rows that failed the same way.
const props = defineProps<{
  executionId: number
  group: FailureGroup | null
}>()

const open = defineModel<boolean>('open', { default: false })
/** Position of the shown row in the group */
const index = defineModel<number>('index', { default: 0 })

const { fetchExecutionRow } = useAnalyses()

const row = ref<ExecutionRow | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const rows = computed(() => props.group?.rows ?? [])
const rowIndex = computed(() => rows.value[index.value] ?? null)

// Latest request wins when the user steps through rows quickly
let request = 0
watch(
  () => [open.value, props.executionId, rowIndex.value] as const,
  async ([isOpen, executionId, selectedRow]) => {
    if (!isOpen || selectedRow === null)
      return
    const current = ++request
    error.value = null
    loading.value = true
    try {
      const data = await fetchExecutionRow(executionId, selectedRow)
      if (current === request)
        row.value = data
    }
    catch (e) {
      if (current === request) {
        row.value = null
        error.value = apiErrorMessage(e) ?? 'Couldn’t load this row.'
      }
    }
    finally {
      if (current === request)
        loading.value = false
    }
  },
  { immediate: true },
)

function step(delta: number) {
  const next = index.value + delta
  if (next >= 0 && next < rows.value.length)
    index.value = next
}

// Typing in a field is left alone: these only fire outside inputs
defineShortcuts({
  j: () => open.value && step(1),
  k: () => open.value && step(-1),
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="`Row ${rowIndex ?? ''}`"
    :description="group?.agent_name ? `Failed at ${group.agent_name}` : 'Failed before reaching the agents'"
    :ui="{ content: 'max-w-xl' }"
  >
    <template #body>
      <!-- The previous row stays on screen while the next one loads, so stepping doesn't flash a spinner -->
      <BaseLoadingState v-if="loading && !row" size="sm" />
      <UAlert
        v-else-if="error"
        color="error"
        variant="subtle"
        icon="i-ph-x-circle-bold"
        :title="error"
      />
      <ExperimentsExecutionRowDetails
        v-else-if="row"
        :row="row"
        class="transition-opacity duration-150 ease-(--ease-out)"
        :class="loading ? 'opacity-60' : 'opacity-100'"
        :aria-busy="loading"
      />
    </template>

    <template v-if="rows.length > 1" #footer>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1">
          <UTooltip text="Previous row" :kbds="['k']">
            <UButton
              icon="i-ph-caret-up-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Previous row"
              :disabled="index <= 0"
              @click="step(-1)"
            />
          </UTooltip>
          <UTooltip text="Next row" :kbds="['j']">
            <UButton
              icon="i-ph-caret-down-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Next row"
              :disabled="index >= rows.length - 1"
              @click="step(1)"
            />
          </UTooltip>
        </div>
        <span class="text-sm text-muted tabular-nums">
          {{ index + 1 }} of {{ rows.length }} rows that failed this way
        </span>
      </div>
    </template>
  </USlideover>
</template>
