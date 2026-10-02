<script setup lang="ts">
import type { AnalysisRunResult } from '~/types'
import { Scatter } from '@unovis/ts'
import { VisAxis, VisLine, VisScatter, VisTooltip, VisXYContainer } from '@unovis/vue'

const props = defineProps<{
  run: AnalysisRunResult
  // Shared across runs so the plots can be compared
  domain: [number, number]
  /** Row of the point shown in the side panel, if any */
  selectedRow?: number | null
}>()

const emit = defineEmits<{
  select: [row: number]
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

// Lucide glyphs inline: the tooltip is an HTML string, outside Vue's icon components
function icon(paths: string) {
  return `<svg class="size-3.5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`
}
const ICONS = {
  row: icon('<line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/><line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/>'),
  truth: icon('<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>'),
  predicted: icon('<path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2M20 14h2M15 13v2M9 13v2"/>'),
  over: icon('<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>'),
  under: icon('<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>'),
  exact: icon('<path d="M20 6 9 17l-5-5"/>'),
  click: icon('<path d="M14 4.1 12 6M5.1 8l-2.9-.8M6 12l-1.9 2M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/>'),
}

// Up to two decimals, no trailing zeros; a real minus sign for negatives
const fmt = (n: number) => String(Number(n.toFixed(2))).replace('-', '−')

function pointTooltip(d: Point) {
  const error = Number((d.pred - d.truth).toFixed(2))
  const delta = error === 0
    ? `<span class="inline-flex items-center gap-1 text-success">${ICONS.exact}Exact</span>`
    : `<span class="inline-flex items-center gap-1 text-muted tabular-nums">${error > 0 ? ICONS.over : ICONS.under}${error > 0 ? '+' : ''}${fmt(error)}</span>`
  const line = (iconSvg: string, label: string, value: string) =>
    `<div class="flex items-center justify-between gap-6"><span class="inline-flex items-center gap-1.5 text-muted">${iconSvg}${label}</span><span class="font-medium tabular-nums text-highlighted">${value}</span></div>`

  return `<div class="min-w-44 text-xs">
    <div class="flex items-center justify-between gap-6 pb-2 mb-2 border-b border-default">
      <span class="inline-flex items-center gap-1.5 text-sm font-semibold text-highlighted">${ICONS.row}Row ${d.row ?? '?'}</span>
      ${delta}
    </div>
    <div class="flex flex-col gap-1.5">
      ${line(ICONS.truth, 'Ground truth', fmt(d.truth))}
      ${line(ICONS.predicted, 'Predicted', fmt(d.pred))}
    </div>
    ${d.row === null
      ? ''
      : `<div class="inline-flex items-center gap-1.5 mt-2 pt-2 w-full border-t border-default text-dimmed">${ICONS.click}Click to open the row</div>`}
  </div>`
}

const triggers = {
  [Scatter.selectors.point]: pointTooltip,
}

const events = {
  [Scatter.selectors.point]: {
    click: (d: Point) => {
      if (d.row !== null)
        emit('select', d.row)
    },
    mouseenter: (d: Point, event: MouseEvent) => {
      if (d.row !== null)
        (event.currentTarget as SVGElement).style.cursor = 'pointer'
    },
  },
}

const isSelected = (d: Point) => d.row !== null && d.row === props.selectedRow
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
        :size="(d: Point) => isSelected(d) ? 12 : 8"
        color="var(--viz-series-1)"
        :stroke-color="(d: Point) => isSelected(d) ? 'var(--ui-text-highlighted)' : undefined"
        :stroke-width="(d: Point) => isSelected(d) ? 2 : 0"
        :events="events"
      />
      <VisAxis type="x" label="Ground truth" :num-ticks="6" />
      <VisAxis type="y" label="Predicted" :num-ticks="6" />
      <VisTooltip :triggers="triggers" />
    </VisXYContainer>
  </div>
</template>
