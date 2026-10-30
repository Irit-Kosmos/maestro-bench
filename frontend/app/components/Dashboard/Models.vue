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
import type { DashboardModelUsage } from '~/types'

// Where the period went, model by model: logo and full name, its share of the spend as a bar,
// then what it cost. Local models cost nothing, so when nothing was spent the share is of the
// tokens, and failing that of the runs. As tall as the activity strip beside it, with as many
// models as that height holds; the list does not make the card taller.
const props = defineProps<{
  models: readonly DashboardModelUsage[]
  loading?: boolean
}>()

// Rows are 24px with 4px between them
const box = useTemplateRef<HTMLElement>('box')
const shown = useFittingRows(box, 28, 5, -3)

const measure = computed<'spend' | 'tokens' | 'runs'>(() => {
  if (props.models.some(m => m.total_cost_usd > 0))
    return 'spend'
  return props.models.some(m => m.total_tokens > 0) ? 'tokens' : 'runs'
})

function amount(model: DashboardModelUsage) {
  return { spend: model.total_cost_usd, tokens: model.total_tokens, runs: model.executions }[measure.value]
}

function figure(model: DashboardModelUsage) {
  return { spend: formatCost(model.total_cost_usd), tokens: formatTokens(model.total_tokens), runs: `${model.executions} runs` }[measure.value]
}

const sorted = computed(() => [...props.models].sort((a, b) => amount(b) - amount(a)))
const total = computed(() => sorted.value.reduce((sum, m) => sum + amount(m), 0) || 1)

const rows = computed(() => sorted.value.slice(0, shown.value).map(model => ({
  key: `${model.provider}/${model.name}`,
  model,
  share: amount(model) / total.value,
  figure: figure(model),
  details: `${model.executions} ${model.executions === 1 ? 'execution' : 'executions'} · ${formatTokens(model.total_tokens)} tokens · ${formatCost(model.total_cost_usd)}`,
})))

const rest = computed(() => sorted.value.slice(shown.value))
const restText = computed(() => rest.value.map(m => `${m.name} ${figure(m)}`).join(', '))

const titleId = useId()
</script>

<template>
  <section :aria-labelledby="titleId" class="flex min-w-0 flex-col gap-2 rounded-lg border border-default px-4 py-3">
    <div class="flex h-4 items-center justify-between gap-2">
      <h3 :id="titleId" class="text-xs font-medium text-muted">
        Models
      </h3>
      <span v-if="rows.length" class="text-xs text-dimmed">
        By {{ measure }}<template v-if="rest.length">
          ·
          <!-- Focusable, so the models left out reach keyboard and touch too, not only the pointer -->
          <UTooltip :text="restText" :delay-duration="150">
            <span tabindex="0" class="rounded-sm underline decoration-dotted underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-inverted">
              {{ rest.length }} more<span class="sr-only">: {{ restText }}</span>
            </span>
          </UTooltip>
        </template>
      </span>
    </div>

    <div v-if="loading" class="flex flex-col gap-2.5">
      <USkeleton v-for="i in 3" :key="i" class="h-4 w-full" />
    </div>

    <!-- On wide screens the list is taken out of the flow: the strip beside sets the height, the list fills it -->
    <div v-else-if="rows.length" ref="box" class="relative min-h-0 flex-1">
      <ul class="flex flex-col gap-1 xl:absolute xl:inset-x-0 xl:top-0">
        <li v-for="row in rows" :key="row.key" class="grid h-6 grid-cols-[minmax(0,1fr)_minmax(3rem,7rem)_2.5rem_3.5rem] items-center gap-3 text-sm" :title="row.details">
          <ModelsLabel :name="row.model.name" :provider="row.model.provider" class="text-highlighted" />
          <span class="h-1.5 overflow-hidden rounded-full bg-elevated" aria-hidden="true">
            <span class="block h-full rounded-full bg-current text-muted" :style="{ width: `${Math.max(row.share * 100, 2)}%` }" />
          </span>
          <span class="text-end text-xs text-muted tabular-nums">{{ Math.round(row.share * 100) }}%</span>
          <span class="text-end text-xs text-toned tabular-nums">{{ row.figure }}</span>
          <span class="sr-only">{{ row.details }}</span>
        </li>
      </ul>
    </div>

    <p v-else class="flex flex-1 items-center text-sm text-muted">
      Nothing ran over this period.
    </p>
  </section>
</template>
