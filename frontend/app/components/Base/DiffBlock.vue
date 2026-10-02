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
        class="flex w-full items-center gap-2 border-s-2 border-transparent bg-elevated/40 px-3 py-1 text-start font-sans text-xs text-muted outline-none hover:bg-elevated focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
        @click="open(entry.index)"
      >
        <UIcon name="i-lucide-chevrons-up-down" class="size-3.5 shrink-0" aria-hidden="true" />
        {{ entry.fold.rows.length }} unchanged {{ entry.fold.rows.length === 1 ? 'line' : 'lines' }}
      </button>

      <div
        v-else
        class="relative min-h-[1.625em] border-s-2 ps-6 pe-3 break-words whitespace-pre-wrap before:absolute before:start-2 before:select-none before:text-[11px]"
        :class="[rowClass[entry.row.kind], { 'diff-reveal': entry.revealed }]"
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

<style scoped>
/* Lines revealed by opening a fold fade in; click-initiated and rare, so a short one is fine */
.diff-reveal {
  animation: diff-reveal 140ms cubic-bezier(0.23, 1, 0.32, 1);
}

@keyframes diff-reveal {
  from {
    opacity: 0;
  }
}
</style>
