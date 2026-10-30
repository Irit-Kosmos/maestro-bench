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
import type { DiffFold, DiffItem, DiffRow } from '~/utils/textDiff'

// Unified text diff: one column, wrapped lines, the words that changed lit up inside their line.
// Unchanged lines far from a change are folded into one row, opened on click.
const props = defineProps<{
  items: readonly DiffItem[]
}>()

type Entry
  = | { type: 'row', row: DiffRow, revealed: boolean }
    | { type: 'fold', fold: DiffFold, index: number }

const opened = ref<ReadonlySet<number>>(new Set())

// Folds that were opened, flattened with the rest so one loop renders everything
const entries = computed<Entry[]>(() =>
  props.items.flatMap((item, index): Entry[] => {
    if (item.kind !== 'fold')
      return [{ type: 'row', row: item, revealed: false }]
    return opened.value.has(index)
      ? item.rows.map(row => ({ type: 'row', row, revealed: true }))
      : [{ type: 'fold', fold: item, index }]
  }),
)

function open(index: number) {
  opened.value = new Set(opened.value).add(index)
}

// Edge colour, tint, and the sign drawn in the margin (a pseudo-element: it is not copied with the text)
const rowClass = {
  ctx: 'border-transparent',
  add: 'border-success bg-success/10 before:text-success before:content-["+"]',
  del: 'border-error bg-error/10 before:text-error before:content-["−"]',
} as const

// Lines revealed by opening a fold fade in; click-initiated and rare, so a short one is fine
const revealClass = 'transition-opacity duration-140 ease-out starting:opacity-0'

const markClass = {
  ctx: '',
  add: 'bg-success/25',
  del: 'bg-error/25 line-through decoration-error/60',
} as const
</script>

<template>
  <div class="overflow-hidden rounded-md border border-default bg-muted/50 font-mono text-[13px] leading-relaxed text-highlighted">
    <template v-for="(entry, position) in entries" :key="position">
      <button
        v-if="entry.type === 'fold'"
        type="button"
        class="flex w-full items-center gap-2 border-s-2 border-transparent bg-elevated/40 px-3 py-1 text-start font-sans text-xs text-muted outline-none first:rounded-t-[calc(var(--radius-md)-1px)] last:rounded-b-[calc(var(--radius-md)-1px)] hover:bg-elevated focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
        @click="open(entry.index)"
      >
        <UIcon name="i-ph-caret-up-down-bold" class="size-3.5 shrink-0" aria-hidden="true" />
        {{ entry.fold.rows.length }} unchanged {{ entry.fold.rows.length === 1 ? 'line' : 'lines' }}
      </button>

      <div
        v-else
        class="relative min-h-[1.625em] border-s-2 ps-6 pe-3 break-words whitespace-pre-wrap first:rounded-t-[calc(var(--radius-md)-1px)] last:rounded-b-[calc(var(--radius-md)-1px)] before:absolute before:start-2 before:select-none before:text-[11px]"
        :class="[rowClass[entry.row.kind], { [revealClass]: entry.revealed }]"
      >
        <template v-for="(part, index) in entry.row.parts" :key="index">
          <mark v-if="part.changed" class="rounded-[3px] text-inherit" :class="markClass[entry.row.kind]">{{ part.text }}</mark><template v-else>
            {{ part.text }}
          </template>
        </template>
        <span v-if="entry.row.whitespace && entry.row.kind === 'add'" class="ms-2 rounded-sm bg-elevated px-1 font-sans text-[10px] text-muted select-none">whitespace</span>
      </div>
    </template>
  </div>
</template>
