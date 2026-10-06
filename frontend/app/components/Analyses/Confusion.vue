<script setup lang="ts">
import { Heatmap } from '@unovis/ts'
import { VisHeatmap, VisSingleContainer, VisTooltip } from '@unovis/vue'

const props = defineProps<{
  labels: string[]
  // rows = ground truth, columns = prediction
  matrix: number[][]
}>()

const { chartWidth } = usePrinting()

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

// Sequential blue ramp, from few rows to many. A square-root scale keeps small
// counts visible next to a dominant diagonal cell. "More" has to stand out from
// the surface: darker on a light page, lighter on a dark one.
const light = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
const dark = ['#17407a', '#1f5aa6', '#2f78d0', '#5496e6', '#82b3f0', '#b3d1f7', '#dbe9fc']
const colorMode = useColorMode()
const ramp = computed(() => colorMode.value === 'dark' ? dark : light)

// A fresh function whenever the theme or the data changes, so Unovis repaints the cells
const cellColor = computed(() => {
  const colors = ramp.value
  const max = maxCount.value
  return (d: Cell): string | undefined => {
    if (!d.count)
      return undefined // rendered as an empty cell
    const t = Math.sqrt(d.count / max)
    return colors[Math.min(colors.length - 1, Math.floor(t * colors.length))]!
  }
})

const triggers = {
  [Heatmap.selectors.cell]: (d: Cell | { datum: Cell }) => {
    const cell = 'datum' in d ? d.datum : d
    return `Truth ${cell.truth} · Predicted ${cell.pred}<br><b>${cell.count}</b> rows`
  },
}
</script>

<template>
  <div class="viz-root">
    <div class="text-xs text-muted mb-1">
      Rows: ground truth · Columns: predicted
    </div>
    <VisSingleContainer :key="chartWidth ?? 'auto'" :data="cells" :width="chartWidth" :duration="chartWidth ? 0 : undefined" :height="Math.min(320, 36 * size + 40)">
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
