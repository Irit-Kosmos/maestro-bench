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
import type { AnalysisRunResult } from '~/types'
import { Scatter } from '@unovis/ts'
import { VisAxis, VisLine, VisScatter, VisTooltip, VisXYContainer } from '@unovis/vue'

const props = defineProps<{
  run: AnalysisRunResult
  // Shared across runs so the plots can be compared
  domain: [number, number]
  /** Row shown in the side panel, if any */
  selectedRow?: number | null
}>()

const emit = defineEmits<{
  /** Every row sitting on the clicked point: scores are often discrete, so several rows share one spot */
  select: [rows: number[]]
}>()

const { chartWidth } = usePrinting()

interface Point {
  truth: number
  pred: number
  x: number
  y: number
  rows: number[]
  /** Rows on this spot, including those without a row index */
  count: number
}

// Rows with the same ground truth and prediction collapse into a single point
const points = computed<Point[]>(() => {
  const spots = new Map<string, Point>()
  for (const p of props.run.points ?? []) {
    const key = `${p.truth}|${p.pred}`
    let spot = spots.get(key)
    if (!spot) {
      spot = { truth: p.truth, pred: p.pred, x: p.truth, y: p.pred, rows: [], count: 0 }
      spots.set(key, spot)
    }
    spot.count++
    if (p.row_index !== null)
      spot.rows.push(p.row_index)
  }
  return [...spots.values()]
})

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
  rows: icon('<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'),
  click: icon('<path d="M14 4.1 12 6M5.1 8l-2.9-.8M6 12l-1.9 2M7.2 2.2 8 5.1"/><path d="M9.037 9.69a.498.498 0 0 1 .653-.653l11 4.5a.5.5 0 0 1-.074.949l-4.349 1.041a1 1 0 0 0-.74.739l-1.04 4.35a.5.5 0 0 1-.95.074z"/>'),
}

// Up to two decimals, no trailing zeros; a real minus sign for negatives
const MAX_LISTED_ROWS = 8

const fmt = (n: number) => String(Number(n.toFixed(2))).replace('-', '−')

function rowsList(rows: number[]) {
  const shown = rows.slice(0, MAX_LISTED_ROWS).join(', ')
  return rows.length > MAX_LISTED_ROWS ? `Rows ${shown} and ${rows.length - MAX_LISTED_ROWS} more` : `Rows ${shown}`
}

function pointTooltip(d: Point) {
  const error = Number((d.pred - d.truth).toFixed(2))
  const delta = error === 0
    ? `<span class="inline-flex items-center gap-1 text-success">${ICONS.exact}Exact</span>`
    : `<span class="inline-flex items-center gap-1 text-muted tabular-nums">${error > 0 ? ICONS.over : ICONS.under}${error > 0 ? '+' : ''}${fmt(error)}</span>`
  const line = (iconSvg: string, label: string, value: string) =>
    `<div class="flex items-center justify-between gap-6"><span class="inline-flex items-center gap-1.5 text-muted">${iconSvg}${label}</span><span class="font-medium tabular-nums text-highlighted">${value}</span></div>`

  return `<div class="min-w-44 text-xs">
    <div class="flex items-center justify-between gap-6 pb-2 mb-2 border-b border-default">
      <span class="inline-flex items-center gap-1.5 text-sm font-semibold text-highlighted">${d.count > 1 ? `${ICONS.rows}${d.count} rows` : `${ICONS.row}Row ${d.rows[0] ?? '?'}`}</span>
      ${delta}
    </div>
    <div class="flex flex-col gap-1.5">
      ${line(ICONS.truth, 'Ground truth', fmt(d.truth))}
      ${line(ICONS.predicted, 'Predicted', fmt(d.pred))}
    </div>
    ${d.count > 1 ? `<div class="mt-2 pt-2 border-t border-default text-muted tabular-nums">${rowsList(d.rows)}</div>` : ''}
    ${d.rows.length === 0
      ? ''
      : `<div class="inline-flex items-center gap-1.5 mt-2 pt-2 w-full border-t border-default text-muted">${ICONS.click}${d.rows.length > 1 ? 'Click to browse the rows' : 'Click to open the row'}</div>`}
  </div>`
}

const triggers = {
  [Scatter.selectors.point]: pointTooltip,
}

const events = {
  [Scatter.selectors.point]: {
    click: (d: Point) => {
      if (d.rows.length)
        emit('select', d.rows)
    },
    mouseenter: (d: Point, event: MouseEvent) => {
      if (d.rows.length)
        (event.currentTarget as SVGElement).style.cursor = 'pointer'
    },
  },
}

const isSelected = (d: Point) => props.selectedRow != null && d.rows.includes(props.selectedRow)

// The plot itself is a picture: this says what it shows, and the list under it makes each point reachable
const summary = computed(() => {
  const total = points.value.reduce((sum, p) => sum + p.count, 0)
  const exact = points.value.reduce((sum, p) => p.pred === p.truth ? sum + p.count : sum, 0)
  return `Predicted against ground truth for ${props.run.label}: ${total} ${total === 1 ? 'row' : 'rows'}, ${exact} predicted exactly`
})

// The list is built only once opened: a continuous score can leave hundreds of points
const listOpen = ref(false)
</script>

<template>
  <div class="viz-root">
    <div role="img" :aria-label="summary">
      <!-- Keyed on the width: a redraw at the new size keeps the old x scale, a fresh chart doesn't -->
      <VisXYContainer
        :key="chartWidth ?? 'auto'"
        :width="chartWidth"
        :height="260"
        :duration="chartWidth ? 0 : undefined"
        :x-domain="domain"
        :y-domain="domain"
      >
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
          :stroke-color="(d: Point) => isSelected(d) ? 'var(--ui-text-highlighted)' : 'var(--viz-series-1)'"
          :stroke-width="(d: Point) => isSelected(d) ? 2 : 1"
          :events="events"
          :duration="0"
        />
        <VisAxis type="x" label="Ground truth" :num-ticks="6" />
        <VisAxis type="y" label="Predicted" :num-ticks="6" />
        <VisTooltip :triggers="triggers" />
      </VisXYContainer>
    </div>

    <details v-if="points.length" class="mt-1 text-xs print:hidden" @toggle="listOpen = ($event.target as HTMLDetailsElement).open">
      <summary class="w-fit cursor-pointer rounded-sm text-muted outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted">
        List the points
      </summary>
      <ul v-if="listOpen" class="mt-1 max-h-40 divide-y divide-default overflow-y-auto rounded-md border border-default">
        <li v-for="p in points" :key="`${p.truth}|${p.pred}`">
          <button
            v-if="p.rows.length"
            type="button"
            class="flex w-full items-center justify-between gap-3 px-2 py-1 text-start outline-none hover:bg-elevated focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
            :aria-current="isSelected(p) || undefined"
            @click="emit('select', p.rows)"
          >
            <span class="text-highlighted">{{ p.count > 1 ? `${p.count} rows` : `Row ${p.rows[0]}` }}</span>
            <span class="text-muted tabular-nums">Truth {{ fmt(p.truth) }} · predicted {{ fmt(p.pred) }}</span>
          </button>
          <p v-else class="flex items-center justify-between gap-3 px-2 py-1">
            <span class="text-highlighted">{{ p.count }} {{ p.count === 1 ? 'row' : 'rows' }}</span>
            <span class="text-muted tabular-nums">Truth {{ fmt(p.truth) }} · predicted {{ fmt(p.pred) }}</span>
          </p>
        </li>
      </ul>
    </details>
  </div>
</template>
