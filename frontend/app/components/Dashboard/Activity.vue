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
import type { DashboardActivity, DashboardBucket, DashboardRange, DashboardTotals } from '~/types'
import type { Change } from '~/utils/dashboard'
import { DASHBOARD_RANGES, failureRate, formatRate, relativeChange } from '~/utils/dashboard'

// What was run over the chosen period (picked above the strip), each figure set against the
// period just before it and drawn slice by slice. Cells are separated
// by 1px of the border color showing through the grid gap, so the dividers stay even when the grid wraps.
const props = defineProps<{
  activity?: DashboardActivity | null
  /** First load: nothing to show yet */
  loading?: boolean
  /** The figures are being replaced, after a new period was picked */
  refreshing?: boolean
}>()

const range = defineModel<DashboardRange>('range', { required: true })

const { formatDate } = useUIHelpers()

const longRange = computed(() => DASHBOARD_RANGES.find(r => r.value === range.value)?.long ?? '')
// What a change is measured against: the period before, or for "all" what it totalled 30 days ago
const against = computed(() => range.value === 'all' ? '30 days ago' : `previous ${longRange.value}`)
const againstLabel = computed(() => against.value.charAt(0).toUpperCase() + against.value.slice(1))

interface Card {
  key: string
  label: string
  value: string
  change: Change
  /** Whether more of it is a bad sign, which colors the change */
  worseWhenUp?: boolean
  /** The change as it reads in a tooltip: what the period before had */
  before: string
  hint: string
  /** The hint in full, when it is cut short */
  hintTitle?: string
  bars: number[]
  /** Formats what a bar stands for, given its slice */
  barLabel: (bucket: DashboardBucket) => string
  /** Tone of the bars */
  barClass: string
  /** Where the hint leads, when what it counts can be looked into */
  hintTo?: string
}

function slice(bucket: DashboardBucket) {
  const date = parseApiDate(bucket.start)
  return ['24h', '7d'].includes(range.value)
    ? formatDate(bucket.start)
    : date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function perExperiment(total: number, totals: DashboardTotals, format: (n: number) => string) {
  return totals.experiments ? `${format(total / totals.experiments)} per experiment` : 'No experiments'
}

const cards = computed<Card[]>(() => {
  const a = props.activity
  if (!a)
    return []
  const { current, previous, buckets } = a
  const plural = (n: number, one: string, many: string) => `${n.toLocaleString('en-US')} ${n === 1 ? one : many}`
  const failures = failureRate(current)

  return [
    {
      key: 'experiments',
      label: 'Experiments',
      value: current.experiments.toLocaleString('en-US'),
      change: relativeChange(current.experiments, previous?.experiments),
      before: String(previous?.experiments ?? ''),
      hint: `${current.completed.toLocaleString('en-US')} completed · ${current.failed.toLocaleString('en-US')} failed`,
      bars: buckets.map(b => b.experiments),
      barLabel: b => `${slice(b)} · ${plural(b.experiments, 'experiment', 'experiments')}`,
      barClass: 'text-muted',
    },
    {
      key: 'tokens',
      label: 'Tokens',
      value: formatTokens(current.total_tokens),
      change: relativeChange(current.total_tokens, previous?.total_tokens),
      before: formatTokens(previous?.total_tokens),
      hint: perExperiment(current.total_tokens, current, formatTokens),
      bars: buckets.map(b => b.total_tokens),
      barLabel: b => `${slice(b)} · ${formatTokens(b.total_tokens)} tokens`,
      barClass: 'text-muted',
    },
    {
      key: 'spend',
      label: 'Spend',
      value: formatCost(current.total_cost_usd),
      change: relativeChange(current.total_cost_usd, previous?.total_cost_usd),
      before: formatCost(previous?.total_cost_usd),
      hint: perExperiment(current.total_cost_usd, current, formatCost),
      bars: buckets.map(b => b.total_cost_usd),
      barLabel: b => `${slice(b)} · ${formatCost(b.total_cost_usd)}`,
      barClass: 'text-muted',
    },
    {
      key: 'failures',
      label: 'Row failures',
      value: formatRate(failures),
      change: relativeChange(current.rows_failed, previous?.rows_failed),
      worseWhenUp: true,
      before: `${(previous?.rows_failed ?? 0).toLocaleString('en-US')} failed rows`,
      // Short, so it stays clear of the bars: the rows behind the rate are in its tooltip
      hint: current.experiments_with_failures
        ? `${plural(current.experiments_with_failures, 'experiment', 'experiments')} affected`
        : current.rows_done ? `${current.rows_failed.toLocaleString('en-US')} of ${current.rows_done.toLocaleString('en-US')} rows` : 'No rows processed',
      hintTitle: current.rows_done
        ? `${current.rows_failed.toLocaleString('en-US')} of ${current.rows_done.toLocaleString('en-US')} rows failed`
        : undefined,
      // The same experiments, over the same period, on the experiments list
      hintTo: current.experiments_with_failures
        ? `/experiments?${new URLSearchParams({ failures: '1', ...(range.value === 'all' ? {} : { range: range.value }) })}`
        : undefined,
      bars: buckets.map(b => b.rows_failed),
      barLabel: b => `${slice(b)} · ${plural(b.rows_failed, 'failed row', 'failed rows')}`,
      barClass: current.rows_failed ? 'text-error' : 'text-muted',
    },
  ]
})

// Only a real change is shown: next to an empty period before, "New" on every figure says nothing
function changeText(change: Change) {
  if (change.kind === 'change')
    return `${Math.abs(change.percent)}%`
  return ''
}

function changeIcon(change: Change) {
  if (change.kind === 'change' && change.percent < 0)
    return 'i-ph-arrow-down-right-bold'
  return change.kind === 'change' && change.percent === 0 ? 'i-ph-minus-bold' : 'i-ph-arrow-up-right-bold'
}

function changeClass(card: Card) {
  const { change } = card
  if (change.kind === 'none' || (change.kind === 'change' && change.percent === 0) || !card.worseWhenUp)
    return 'text-muted'
  return change.kind === 'new' || change.percent > 0 ? 'text-error' : 'text-success'
}
</script>

<template>
  <!-- The page titles this block: no heading of its own -->
  <div class="@container h-full">
    <div
      class="grid h-full grid-cols-1 @md:grid-cols-2 max-xl:@4xl:grid-cols-4 gap-px rounded-lg border border-default bg-(--ui-border) overflow-hidden motion-safe:transition-opacity"
      :class="{ 'opacity-60': refreshing }"
      :aria-busy="loading || refreshing"
    >
      <template v-if="loading || !activity">
        <div v-for="i in 4" :key="i" class="flex flex-col justify-center gap-1.5 bg-default px-4 py-3">
          <USkeleton class="h-3 w-20" />
          <USkeleton class="h-7 w-full" />
          <USkeleton class="h-3 w-28" />
        </div>
      </template>

      <template v-else>
        <div v-for="card in cards" :key="card.key" class="flex min-w-0 flex-col justify-center gap-1.5 bg-default px-4 py-3">
          <!-- Fixed height: the change badge must not make the header taller than when it is absent -->
          <div class="flex h-4 items-center justify-between gap-2">
            <span class="text-xs font-medium text-muted">{{ card.label }}</span>
            <UTooltip
              v-if="card.change.kind === 'change'"
              :text="`${againstLabel}: ${card.before}`"
              :delay-duration="150"
            >
              <span
                tabindex="0"
                class="inline-flex items-center gap-0.5 rounded-sm text-xs tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-inverted"
                :class="changeClass(card)"
              >
                <UIcon :name="changeIcon(card.change)" class="size-3" aria-hidden="true" />
                {{ changeText(card.change) }}
                <span class="sr-only">vs {{ against }}: {{ card.before }}</span>
              </span>
            </UTooltip>
          </div>

          <!-- The bars sit at the bottom right, level with the hint, which is cut before it reaches them -->
          <div class="grid grid-cols-[minmax(0,1fr)_auto] items-end gap-x-3 gap-y-1.5">
            <span class="text-xl font-semibold text-highlighted tabular-nums leading-7">{{ card.value }}</span>
            <DashboardSparkline
              :values="card.bars"
              :labels="activity.buckets.map(card.barLabel)"
              class="row-span-2"
              :class="card.barClass"
            />
            <NuxtLink
              v-if="card.hintTo"
              :to="card.hintTo"
              :title="card.hintTitle"
              class="-mx-1 flex min-w-0 items-center gap-1 rounded px-1 text-xs text-error tabular-nums outline-none hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
            >
              <span class="truncate">{{ card.hint }}</span>
              <UIcon name="i-ph-arrow-right-bold" class="size-3 shrink-0" aria-hidden="true" />
            </NuxtLink>
            <span v-else class="truncate text-xs text-muted tabular-nums" :title="card.hintTitle ?? card.hint">{{ card.hint }}</span>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>
