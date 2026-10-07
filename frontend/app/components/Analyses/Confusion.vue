<script setup lang="ts">
import { Heatmap } from '@unovis/ts'
import { VisHeatmap, VisSingleContainer, VisTooltip } from '@unovis/vue'

const props = defineProps<{
  labels: string[]
  // rows = ground truth, columns = prediction
  matrix: number[][]
  /** Dataset rows behind each cell, same shape as `matrix` */
  rows?: number[][][]
}>()

const emit = defineEmits<{
  /** Every dataset row counted in the clicked cell */
  select: [rows: number[]]
}>()

const { chartWidth } = usePrinting()

interface Cell {
  truth: string
  pred: string
  count: number
  /** Rows of the whole ground-truth class, to show the share this cell holds */
  truthTotal: number
  rows: number[]
}

const cells = computed<Cell[]>(() => props.matrix.flatMap((row, i) => {
  const truthTotal = row.reduce((sum, n) => sum + n, 0)
  return row.map((count, j) => ({
    truth: props.labels[i]!,
    pred: props.labels[j]!,
    count,
    truthTotal,
    rows: props.rows?.[i]?.[j] ?? [],
  }))
}))

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

// Lucide glyphs inline: the tooltip is an HTML string, outside Vue's icon components
function icon(paths: string) {
  return `<svg class="size-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`
}
const ICONS = {
  truth: icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'),
  predicted: icon('<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>'),
  share: icon('<line x1="19" x2="5" y1="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>'),
  rows: icon('<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'),
  correct: icon('<path d="M20 6 9 17l-5-5"/>'),
  wrong: icon('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
  click: icon('<path d="M14 4.1 12 6M5.1 8l-2.9-.8M6 12l-1.9 2M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/>'),
}

const escapeHtml = (str: string) => str.replace(/[&<>"']/g, c => `&#${c.charCodeAt(0)};`)

const MAX_LISTED_ROWS = 8

function rowsList(rows: number[]) {
  const shown = rows.slice(0, MAX_LISTED_ROWS).join(', ')
  return rows.length > MAX_LISTED_ROWS ? `Rows ${shown} and ${rows.length - MAX_LISTED_ROWS} more` : `Rows ${shown}`
}

// Unovis hands the datum bare or wrapped depending on the version
const datumOf = (d: Cell | { datum: Cell }) => 'datum' in d ? d.datum : d

function cellTooltip(d: Cell | { datum: Cell }) {
  const cell = datumOf(d)
  const line = (iconSvg: string, label: string, value: string) =>
    `<div class="flex items-center justify-between gap-6"><span class="inline-flex items-center gap-1.5 text-muted">${iconSvg}${label}</span><span class="font-medium tabular-nums text-highlighted">${value}</span></div>`
  const verdict = cell.truth === cell.pred
    ? `<span class="inline-flex items-center gap-1 text-success">${ICONS.correct}Correct</span>`
    : `<span class="inline-flex items-center gap-1 text-muted">${ICONS.wrong}Misclassified</span>`
  const share = cell.truthTotal ? `${Math.round(cell.count / cell.truthTotal * 100)}%` : '–'
  const title = `${cell.count} ${cell.count === 1 ? 'row' : 'rows'}`

  return `<div class="min-w-44 text-xs">
    <div class="flex items-center justify-between gap-6 pb-2 mb-2 border-b border-default">
      <span class="inline-flex items-center gap-1.5 text-sm font-semibold text-highlighted">${ICONS.rows}${title}</span>
      ${cell.count ? verdict : ''}
    </div>
    <div class="flex flex-col gap-1.5">
      ${line(ICONS.truth, 'Ground truth', escapeHtml(cell.truth))}
      ${line(ICONS.predicted, 'Predicted', escapeHtml(cell.pred))}
      ${cell.count ? line(ICONS.share, `Of ${escapeHtml(cell.truth)}`, share) : ''}
    </div>
    ${cell.rows.length > 1 ? `<div class="mt-2 pt-2 border-t border-default text-muted tabular-nums">${rowsList(cell.rows)}</div>` : ''}
    ${cell.rows.length === 0
      ? ''
      : `<div class="inline-flex items-center gap-1.5 mt-2 pt-2 w-full border-t border-default text-dimmed">${ICONS.click}${cell.rows.length > 1 ? 'Click to browse the rows' : 'Click to open the row'}</div>`}
  </div>`
}

const triggers = {
  [Heatmap.selectors.cell]: cellTooltip,
}

const events = {
  [Heatmap.selectors.cell]: {
    click: (d: Cell | { datum: Cell }) => {
      const { rows } = datumOf(d)
      if (rows.length)
        emit('select', rows)
    },
    mouseenter: (d: Cell | { datum: Cell }, event: MouseEvent) => {
      if (datumOf(d).rows.length)
        (event.currentTarget as SVGElement).style.cursor = 'pointer'
    },
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
        :events="events"
      />
      <VisTooltip :triggers="triggers" />
    </VisSingleContainer>
  </div>
</template>
