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

function tooltip(b: Bar) {
  if (b.value === null)
    return `<b>${b.label}</b><br>${b.reason ?? 'Undefined'}`
  const ci = b.low !== null && b.high !== null
    ? `<br>${Math.round(props.confidence * 100)}% CI [${formatMetric(b.low)}, ${formatMetric(b.high)}]`
    : ''
  return `<b>${b.label}</b><br>${props.metric.label} ${formatMetric(b.value)}${ci}`
}

const triggers = {
  [GroupedBar.selectors.bar]: (d: Bar) => tooltip(d),
  [Boxplot.selectors.boxGroup]: (d: Bar) => tooltip(d),
}
</script>

<template>
  <div class="viz-root">
    <div class="flex items-baseline justify-between mb-2">
      <h4 class="text-sm font-semibold text-neutral-800">
        {{ metric.label }}
      </h4>
      <span v-if="metric.lower_is_better" class="text-xs text-neutral-500">lower is better</span>
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
    <p v-else class="text-sm text-neutral-500 py-8 text-center">
      Undefined for every run
    </p>
  </div>
</template>
