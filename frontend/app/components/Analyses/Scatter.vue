<script setup lang="ts">
import type { AnalysisRunResult } from '~/types'
import { Scatter } from '@unovis/ts'
import { VisAxis, VisLine, VisScatter, VisTooltip, VisXYContainer } from '@unovis/vue'

const props = defineProps<{
  run: AnalysisRunResult
  // Shared across runs so the plots can be compared
  domain: [number, number]
}>()

interface Point {
  truth: number
  pred: number
  x: number
  y: number
  row: number | null
}

const points = computed<Point[]>(() => (props.run.points ?? []).map(p => ({
  truth: p.truth,
  pred: p.pred,
  x: p.truth,
  y: p.pred,
  row: p.row_index,
})))

const diagonal = computed(() => [
  { x: props.domain[0], y: props.domain[0] },
  { x: props.domain[1], y: props.domain[1] },
])

const triggers = {
  [Scatter.selectors.point]: (d: Point) =>
    `Row ${d.row ?? '?'}<br>Truth ${d.truth} · Predicted ${d.pred}`,
}
</script>

<template>
  <div class="viz-root">
    <VisXYContainer :height="260" :x-domain="domain" :y-domain="domain">
      <VisLine
        :data="diagonal"
        :x="(d: { x: number }) => d.x"
        :y="(d: { y: number }) => d.y"
        color="var(--viz-reference)"
        :line-width="1"
        :line-dash-array="[4, 4]"
      />
      <VisScatter
        :data="points"
        :x="(d: Point) => d.x"
        :y="(d: Point) => d.y"
        :size="8"
        color="var(--viz-series-1)"
      />
      <VisAxis type="x" label="Ground truth" :num-ticks="6" />
      <VisAxis type="y" label="Predicted" :num-ticks="6" />
      <VisTooltip :triggers="triggers" />
    </VisXYContainer>
  </div>
</template>
