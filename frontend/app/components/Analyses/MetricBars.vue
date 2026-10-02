<script setup lang="ts">
import type { AnalysisRunResult, MetricInfo } from '~/types'
import { Boxplot, GroupedBar } from '@unovis/ts'
import { VisAxis, VisBoxplot, VisGroupedBar, VisTooltip, VisXYContainer } from '@unovis/vue'

const props = defineProps<{
  metric: MetricInfo
  runs: AnalysisRunResult[]
  confidence: number
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

const hasValues = computed(() => bars.value.some(b => b.value !== null))

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
  const values = bars.value.map(o => o.value).filter((v): v is number => v !== null)
  if (b.value === null || values.length < 2)
    return null
  const better = values.filter(v => props.metric.lower_is_better ? v < b.value! : v > b.value!).length
  return { position: better + 1, total: values.length }
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
    ${props.metric.lower_is_better ? `<div class="mt-2 pt-2 border-t border-default text-dimmed">Lower is better</div>` : ''}
  </div>`
}

const triggers = {
  [GroupedBar.selectors.bar]: (d: Bar) => tooltip(d),
  [Boxplot.selectors.boxGroup]: (d: Bar) => tooltip(d),
}
</script>

<template>
  <div class="viz-root">
    <div class="flex items-baseline justify-between mb-2">
      <h4 class="text-sm font-semibold text-highlighted">
        {{ metric.label }}
      </h4>
      <span v-if="metric.lower_is_better" class="text-xs text-muted">lower is better</span>
    </div>
    <VisXYContainer v-if="hasValues" :data="bars" :height="200" :padding="{ top: 8 }">
      <VisGroupedBar
        :x="(d: Bar) => d.x"
        :y="[(d: Bar) => d.value ?? undefined]"
        :group-max-width="24"
        :rounded-corners="4"
      />
      <VisBoxplot
        :x="(d: Bar) => d.x"
        :median="(d: Bar) => d.value ?? undefined"
        :quartiles="(d: Bar) => d.value !== null ? [d.value, d.value] : undefined"
        :whiskers="(d: Bar) => d.low !== null && d.high !== null ? [d.low, d.high] : undefined"
        :bar-width="12"
      />
      <VisAxis
        type="x"
        :tick-values="bars.map(b => b.x)"
        :tick-format="(i: number) => bars[i]?.label ?? ''"
        tick-text-fit-mode="trim"
        :tick-text-width="110"
        :grid-line="false"
      />
      <VisAxis type="y" :num-ticks="4" />
      <VisTooltip :triggers="triggers" />
    </VisXYContainer>
    <p v-else class="text-sm text-muted py-8 text-center">
      Undefined for every run
    </p>
  </div>
</template>
