<script setup lang="ts">
import { Heatmap } from '@unovis/ts'
import { VisHeatmap, VisSingleContainer, VisTooltip } from '@unovis/vue'

const props = defineProps<{
  labels: string[]
  // rows = ground truth, columns = prediction
  matrix: number[][]
}>()

interface Cell {
  truth: string
  pred: string
  count: number
}

const cells = computed<Cell[]>(() => props.matrix.flatMap((row, i) =>
  row.map((count, j) => ({ truth: props.labels[i]!, pred: props.labels[j]!, count })),
))

const size = computed(() => props.labels.length)
const maxCount = computed(() => Math.max(1, ...cells.value.map(c => c.count)))

// Sequential blue ramp, light (few rows) to dark (many rows). A square-root
// scale keeps small counts visible next to a dominant diagonal cell.
const ramp = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']

function cellColor(d: Cell): string | undefined {
  if (!d.count)
    return undefined // rendered as an empty cell
  const t = Math.sqrt(d.count / maxCount.value)
  return ramp[Math.min(ramp.length - 1, Math.floor(t * ramp.length))]!
}

const triggers = {
  [Heatmap.selectors.cell]: (d: Cell | { datum: Cell }) => {
    const cell = 'datum' in d ? d.datum : d
    return `Truth ${cell.truth} · Predicted ${cell.pred}<br><b>${cell.count}</b> rows`
  },
}
</script>

<template>
  <div class="viz-root">
    <div class="text-xs text-neutral-500 mb-1">
      Rows: ground truth · Columns: predicted
    </div>
    <VisSingleContainer :data="cells" :height="Math.min(320, 36 * size + 40)">
      <VisHeatmap
        :value="(d: Cell) => d.count || undefined"
        :color="cellColor"
        layout="row"
        :num-rows="size"
        :num-columns="size"
        :row-label="(i: number) => labels[i]"
        :column-label="(i: number) => labels[i]"
      />
      <VisTooltip :triggers="triggers" />
    </VisSingleContainer>
  </div>
</template>
