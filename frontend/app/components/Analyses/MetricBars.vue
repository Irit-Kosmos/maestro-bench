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
import type { AnalysisRunResult, MetricInfo } from '~/types'
import { Boxplot, GroupedBar } from '@unovis/ts'
import { VisAxis, VisBoxplot, VisGroupedBar, VisTooltip, VisXYContainer } from '@unovis/vue'
import { useElementSize } from '@vueuse/core'

const props = defineProps<{
  metric: MetricInfo
  runs: AnalysisRunResult[]
  confidence: number
  /** Dim every bar but the best one */
  highlightBest?: boolean
}>()

interface Bar {
  x: number
  label: string
  value: number | null
  low: number | null
  high: number | null
  reason: string | null
}

const bars = computed<Bar[]>(() => props.runs.map((run, i) => {
  const m = run.metrics[props.metric.key]
  return {
    x: i,
    label: run.label,
    value: m?.value ?? null,
    low: m?.ci_low ?? null,
    high: m?.ci_high ?? null,
    reason: m?.undefined_reason ?? null,
  }
}))

// Width taken by the y axis and the chart's right edge, out of the space shared by the x labels
const AXIS_GUTTER = 48
const root = ref<HTMLElement>()
const { width: rootWidth } = useElementSize(root)
const { chartWidth } = usePrinting()

// Each label gets at most its slot, so neighbours never overlap; the full name stays in the tooltip
const tickTextWidth = computed(() => {
  const width = chartWidth.value ?? rootWidth.value
  if (!width || !bars.value.length)
    return 110
  return Math.max(32, Math.min(110, Math.floor((width - AXIS_GUTTER) / bars.value.length) - 8))
})

const hasValues = computed(() => bars.value.some(b => b.value !== null))

const score = (b: Bar) => metricRankScore(props.metric, b.value!)

// Bars sharing the best value (ties included); empty when there is nothing to rank
const bestX = computed(() => {
  const defined = bars.value.filter(b => b.value !== null)
  if (defined.length < 2)
    return new Set<number>()
  const best = Math.min(...defined.map(score))
  return new Set(defined.filter(b => score(b) === best).map(b => b.x))
})

// Unovis only re-renders when an accessor changes identity, so the state is read
// while the computed evaluates (not inside the returned function) to get a new one per toggle
const dimOthers = computed(() => props.highlightBest && bestX.value.size > 0)

const barColor = computed(() => {
  const dim = dimOthers.value
  return (b: Bar) => dim && !bestX.value.has(b.x)
    ? 'color-mix(in oklab, var(--viz-series-1) 25%, transparent)'
    : undefined
})

// One neutral colour for every whisker, visible over the bars as well
const whiskerColor = computed(() => {
  const dim = dimOthers.value
  return (b: Bar) => dim && !bestX.value.has(b.x)
    ? 'color-mix(in oklab, var(--viz-reference) 25%, transparent)'
    : 'var(--viz-reference)'
})

// Lucide glyphs inline: the tooltip is an HTML string, outside Vue's icon components
function icon(paths: string) {
  return `<svg class="size-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`
}
const ICONS = {
  run: icon('<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>'),
  value: icon('<path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/>'),
  interval: icon('<path d="m18 8 4 4-4 4"/><path d="m6 8-4 4 4 4"/><path d="M2 12h20"/>'),
  undefinedValue: icon('<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/>'),
}

const escapeHtml = (str: string) => str.replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`)

// 1 = best run for this metric; null when there is nothing to rank
function rank(b: Bar) {
  const total = bars.value.filter(o => o.value !== null).length
  if (b.value === null || total < 2)
    return null
  const mine = score(b)
  const better = bars.value.filter(o => o.value !== null && score(o) < mine).length
  return { position: better + 1, total }
}

function tooltip(b: Bar) {
  const r = rank(b)
  const rankLabel = r
    ? `<span class="${r.position === 1 ? 'text-success' : 'text-muted'} tabular-nums">${r.position === 1 ? 'Best' : `${r.position} / ${r.total}`}</span>`
    : ''
  const header = `<div class="flex items-center justify-between gap-6 pb-2 mb-2 border-b border-default">
      <span class="inline-flex items-center gap-1.5 text-sm font-semibold text-highlighted min-w-0"><span class="shrink-0">${ICONS.run}</span><span class="truncate max-w-56">${escapeHtml(b.label)}</span></span>
      ${rankLabel}
    </div>`
  const line = (iconSvg: string, label: string, value: string) =>
    `<div class="flex items-center justify-between gap-6"><span class="inline-flex items-center gap-1.5 text-muted">${iconSvg}${label}</span><span class="font-medium tabular-nums text-highlighted">${value}</span></div>`

  if (b.value === null) {
    return `<div class="min-w-44 max-w-64 text-xs">${header}
      <div class="flex items-start gap-1.5 text-muted">${ICONS.undefinedValue}<span>${escapeHtml(b.reason ?? 'Undefined')}</span></div>
    </div>`
  }

  const ci = b.low !== null && b.high !== null
    ? line(ICONS.interval, `${Math.round(props.confidence * 100)}% CI`, `${formatMetric(b.low)} – ${formatMetric(b.high)}`)
    : ''
  return `<div class="min-w-44 text-xs">${header}
    <div class="flex flex-col gap-1.5">
      ${line(ICONS.value, escapeHtml(props.metric.label), formatMetric(b.value))}
      ${ci}
    </div>
    ${props.metric.lower_is_better ? `<div class="mt-2 pt-2 border-t border-default text-muted">Lower is better</div>` : ''}
  </div>`
}

const triggers = {
  [GroupedBar.selectors.bar]: (d: Bar) => tooltip(d),
  // Boxplot binds its own wrapper around the datum
  [Boxplot.selectors.boxGroup]: (d: { datum: Bar }) => tooltip(d.datum),
}
</script>

<template>
  <div ref="root" class="viz-root">
    <div class="flex items-baseline justify-between mb-2">
      <h3 class="text-sm font-semibold text-highlighted">
        {{ metric.label }}
      </h3>
      <span v-if="metric.lower_is_better" class="text-xs text-muted">lower is better</span>
    </div>
    <div v-if="hasValues" role="img" :aria-label="`${metric.label} for ${bars.length} ${bars.length === 1 ? 'execution' : 'executions'}, with confidence intervals`">
      <VisXYContainer :data="bars" :width="chartWidth" :height="200" :padding="{ top: 8 }">
        <VisGroupedBar
          :x="(d: Bar) => d.x"
          :y="[(d: Bar) => d.value ?? undefined]"
          :group-max-width="24"
          :rounded-corners="4"
          :color="barColor"
          :duration="0"
        />
        <VisBoxplot
          :x="(d: Bar) => d.x"
          :median="(d: Bar) => d.value ?? undefined"
          :quartiles="(d: Bar) => d.value !== null ? [d.value, d.value] : undefined"
          :whiskers="(d: Bar) => d.low !== null && d.high !== null ? [d.low, d.high] : undefined"
          :bar-width="12"
          :color="whiskerColor"
          :duration="0"
        />
        <VisAxis
          type="x"
          :tick-values="bars.map(b => b.x)"
          :tick-format="(i: number) => bars[i]?.label ?? ''"
          tick-text-fit-mode="trim"
          :tick-text-width="tickTextWidth"
          :grid-line="false"
        />
        <VisAxis type="y" :num-ticks="4" />
        <VisTooltip :triggers="triggers" />
      </VisXYContainer>
    </div>
    <p v-else class="text-sm text-muted py-8 text-center">
      Undefined for every execution
    </p>
    <!-- The values the chart would show on hover, written out: on paper there is no tooltip, and a screen reader has no bars -->
    <ul v-if="hasValues" class="sr-only print:not-sr-only mt-1 space-y-0.5 text-xs">
      <li v-for="b in bars" :key="b.x" class="flex items-baseline justify-between gap-3">
        <span class="truncate text-muted">{{ b.label }}</span>
        <span v-if="b.value !== null" class="shrink-0 tabular-nums text-highlighted" :class="rank(b)?.position === 1 && 'font-semibold'">
          {{ formatMetric(b.value) }}
          <span v-if="b.low !== null && b.high !== null" class="font-normal text-muted">
            [{{ formatMetric(b.low) }}, {{ formatMetric(b.high) }}]
          </span>
        </span>
        <span v-else class="shrink-0 text-muted">—</span>
      </li>
    </ul>
  </div>
</template>
