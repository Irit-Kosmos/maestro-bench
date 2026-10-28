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
import type { DashboardExperiment } from '~/types'

// Recent runs, two lines each, as the recent work beside: the name, then where it comes from (its
// batch, which the line leads to, and its dataset). Inside a batch the experiments share most of
// their name, so they are named by the values they vary alone ("mistral-small-2503 · Content A"),
// the axes being in the tooltip. Columns appear as the block gets wider (container queries, so a
// resized sidebar counts too), in order of importance.
const props = defineProps<{
  experiments: readonly DashboardExperiment[]
  loading?: boolean
  /** How many rows to show at most */
  maxRows?: number
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()

const shown = computed(() => props.experiments.slice(0, props.maxRows ?? 8))

const grid = 'grid items-center gap-x-4 px-4 grid-cols-[1rem_minmax(0,1fr)_4.5rem] @xl:grid-cols-[1rem_minmax(0,1.2fr)_minmax(0,1fr)_4rem_1.25rem_4.5rem] @4xl:grid-cols-[1rem_minmax(0,1.4fr)_minmax(0,1fr)_3.5rem_4rem_1.25rem_4.5rem]'
const show = {
  models: 'hidden @xl:block',
  rows: 'hidden @4xl:block',
  cost: 'hidden @xl:block',
  author: 'hidden @xl:flex',
}
const head = 'text-xs text-muted truncate'

// "Language: mistral-small-2503" → "mistral-small-2503": what tells the batch's experiments apart
function variedValues(exp: DashboardExperiment) {
  const { segments, batch } = splitExperimentName(exp.name, exp.batch_name)
  if (!batch)
    return segments
  return segments.map((segment) => {
    const colon = segment.indexOf(': ')
    return colon > 0 ? segment.slice(colon + 2) : segment
  })
}
</script>

<template>
  <div class="@container">
    <!-- Column labels: the rows below carry the same information for assistive tech -->
    <div class="h-8 border-b border-default" :class="[grid]" aria-hidden="true">
      <span />
      <span :class="head">Experiment</span>
      <span :class="[head, show.models]">Models</span>
      <span class="text-right" :class="[head, show.rows]">Rows</span>
      <span class="text-right" :class="[head, show.cost]">Cost</span>
      <span :class="[head, show.author]" title="Created by">By</span>
      <span class="text-right" :class="[head]">When</span>
    </div>

    <div v-if="loading" class="divide-y divide-default">
      <div v-for="i in 6" :key="i" class="h-12 px-4 flex items-center gap-3">
        <USkeleton class="size-3.5 rounded-full" />
        <div class="flex flex-col gap-1.5">
          <USkeleton class="h-3.5 w-48" />
          <USkeleton class="h-3 w-28" />
        </div>
        <USkeleton class="h-3 w-12 ms-auto" />
      </div>
    </div>

    <ul v-else class="divide-y divide-default">
      <!-- An empty link stretches over the row (the name can't be the link: the batch link sits in the row) -->
      <li
        v-for="exp in shown"
        :key="exp.id"
        class="relative hover:bg-elevated/50"
      >
        <NuxtLink
          :to="`/experiments/${exp.id}`"
          :aria-label="`Open experiment ${exp.name}`"
          class="absolute inset-0 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
        />
        <div class="h-12" :class="[grid]">
          <UIStatusIcon :status="exp.status" />

          <span class="flex min-w-0 flex-col">
            <span class="truncate text-sm text-highlighted" :title="exp.name">
              <template v-for="(value, i) in variedValues(exp)" :key="i">
                <span v-if="i > 0" class="text-dimmed" aria-hidden="true"> · </span>
                <span :class="i === 0 ? 'font-medium' : 'text-default'">{{ value }}</span>
              </template>
            </span>
            <span class="flex min-w-0 items-center gap-1 text-xs text-muted">
              <!-- Above the row link: this part opens the batch -->
              <NuxtLink
                v-if="exp.batch_id"
                :to="`/batches/${exp.batch_id}`"
                :aria-label="`Open batch ${exp.batch_name}`"
                class="relative z-1 flex min-w-0 shrink items-center gap-1 rounded text-toned outline-none hover:text-highlighted hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
              >
                <UIcon name="i-ph-arrows-split-bold" class="size-3 shrink-0 text-dimmed" aria-hidden="true" />
                <span class="truncate" :title="`Batch: ${exp.batch_name}`">{{ exp.batch_name }}</span>
              </NuxtLink>
              <span v-if="exp.batch_id && exp.dataset_name" class="text-dimmed" aria-hidden="true">·</span>
              <span v-if="exp.dataset_name" class="flex min-w-0 shrink-[2] items-center gap-1" :title="`Dataset: ${exp.dataset_name}`">
                <UIcon name="i-ph-database-bold" class="size-3 shrink-0 text-dimmed" aria-hidden="true" />
                <span class="sr-only">on dataset</span>
                <span class="truncate">{{ exp.dataset_name }}</span>
              </span>
            </span>
          </span>

          <div class="min-w-0 text-xs text-default" :class="[show.models]">
            <ModelsStack :models="exp.models" />
          </div>

          <UIRowCount :rows="exp.row_count" tone="quiet" class="text-right text-xs" :class="[show.rows]" />

          <span
            class="text-right text-xs text-default tabular-nums" :class="[show.cost]"
            :title="formatCostPrecise(exp.total_cost_usd)"
          >
            {{ formatCost(exp.total_cost_usd) }}
          </span>

          <!-- Above the row link, so its name shows on hover -->
          <span class="relative z-1 items-center" :class="[show.author]">
            <UIPerson :person="exp.author" label="Created by" avatar-only />
          </span>

          <span class="whitespace-nowrap text-right text-xs text-muted tabular-nums" :title="formatDate(exp.created_at)">
            {{ formatRelativeDate(exp.created_at) }}
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>
