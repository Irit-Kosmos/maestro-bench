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

// Recent runs, one line each. Columns appear as the block gets wider (container queries, so a
// resized sidebar counts too): the name and when always stay, the rest in order of importance.
defineProps<{
  experiments: readonly DashboardExperiment[]
  loading?: boolean
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()

const grid = 'grid items-center gap-x-4 px-4 grid-cols-[1rem_minmax(0,1fr)_3.5rem] @2xl:grid-cols-[1rem_minmax(0,1fr)_minmax(0,10rem)_4.5rem_3.5rem] @4xl:grid-cols-[1rem_minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4rem_4.5rem_4.5rem_3.5rem] @6xl:grid-cols-[1rem_minmax(0,2fr)_minmax(0,1fr)_minmax(0,1fr)_4rem_4.5rem_4rem_4.5rem_3.5rem]'
const show = {
  models: 'hidden @2xl:block',
  cost: 'hidden @2xl:block',
  dataset: 'hidden @4xl:block',
  rows: 'hidden @4xl:block',
  duration: 'hidden @4xl:block',
  tokens: 'hidden @6xl:block',
}
const head = 'text-xs text-muted truncate'
</script>

<template>
  <div class="@container">
    <!-- Column labels: the rows below carry the same information for assistive tech -->
    <div v-if="!loading" class="h-8 border-b border-default" :class="[grid]" aria-hidden="true">
      <span />
      <span :class="head">Experiment</span>
      <span :class="[head, show.models]">Models</span>
      <span :class="[head, show.dataset]">Dataset</span>
      <span class="text-right" :class="[head, show.rows]">Rows</span>
      <span class="text-right" :class="[head, show.duration]">Duration</span>
      <span class="text-right" :class="[head, show.tokens]">Tokens</span>
      <span class="text-right" :class="[head, show.cost]">Cost</span>
      <span class="text-right" :class="[head]">When</span>
    </div>

    <div v-if="loading" class="divide-y divide-default">
      <div v-for="i in 6" :key="i" class="h-14 px-4 flex items-center gap-3">
        <USkeleton class="size-3.5 rounded-full" />
        <USkeleton class="h-3.5 w-56" />
        <USkeleton class="h-3 w-16 ms-auto" />
      </div>
    </div>

    <ul v-else class="divide-y divide-default">
      <!-- An empty link stretches over the row (the name can't be the link: the batch link sits inside it) -->
      <li
        v-for="exp in experiments"
        :key="exp.id"
        class="relative hover:bg-elevated/50"
      >
        <NuxtLink
          :to="`/experiments/${exp.id}`"
          :aria-label="`Open experiment ${exp.name}`"
          class="absolute inset-0 outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
        />
        <div class="h-14" :class="[grid]">
          <UIStatusIcon :status="exp.status" />

          <ExperimentsName
            class="text-sm font-medium text-highlighted"
            :name="exp.name"
            :batch-name="exp.batch_name"
            :hint="`#${exp.id}`"
            stacked
          >
            <template v-if="exp.batch_id" #after>
              <NuxtLink
                :to="`/batches/${exp.batch_id}`"
                :title="`Batch: ${exp.batch_name}`"
                :aria-label="`Open batch ${exp.batch_name}`"
                class="relative z-1 shrink-0 self-center rounded text-muted outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
              >
                <UIcon name="i-ph-arrows-split-bold" class="size-3.5 block" aria-hidden="true" />
              </NuxtLink>
            </template>
          </ExperimentsName>

          <div class="min-w-0 text-xs text-toned" :class="[show.models]">
            <ModelsStack :models="exp.models" />
          </div>

          <!-- Above the row link so the full name shows on hover, and it opens the experiment like the rest of the row -->
          <span
            class="relative z-1 cursor-pointer truncate text-xs text-muted"
            :class="[show.dataset]"
            :title="exp.dataset_name ?? undefined"
            @click="navigateTo(`/experiments/${exp.id}`)"
          >
            {{ exp.dataset_name ?? '—' }}
          </span>

          <UIRowCount :rows="exp.row_count" tone="quiet" class="text-right text-xs" :class="[show.rows]" />

          <span class="text-right text-xs text-muted tabular-nums" :class="[show.duration]">
            {{ formatElapsed(exp.duration_seconds) }}
          </span>

          <span
            class="text-right text-xs text-muted tabular-nums" :class="[show.tokens]"
            :title="exp.total_tokens != null ? `${exp.total_tokens.toLocaleString('en-US')} tokens` : undefined"
          >
            {{ formatTokens(exp.total_tokens) }}
          </span>

          <span class="text-right text-xs text-toned tabular-nums" :class="[show.cost]">
            {{ formatCost(exp.total_cost_usd) }}
          </span>

          <span class="text-right text-xs text-muted tabular-nums" :title="formatDate(exp.created_at)">
            {{ formatRelativeDate(exp.created_at) }}
          </span>
        </div>
      </li>
    </ul>
  </div>
</template>
