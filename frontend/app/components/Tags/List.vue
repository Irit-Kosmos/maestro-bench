<script setup lang="ts">
import type { Tag } from '~/types'

// The tags of a row, on one line: the first few, then how many more there are.
// `selectable` makes each tag a button that says which one was clicked.
// Given the `kind` and `id` of the row, hovering the cell (or focusing into it) shows a "+" that opens the tag
// picker, to tag the row without opening it; `changed` says the list should be read again.
const props = withDefaults(defineProps<{
  tags: Tag[]
  max?: number
  selectable?: boolean
  kind?: 'prompt' | 'analysis'
  id?: number
}>(), {
  max: 3,
})

const emit = defineEmits<{
  select: [tag: Tag]
  changed: []
}>()

const shown = computed(() => props.tags.slice(0, props.max))
const hidden = computed(() => props.tags.slice(props.max))
const editable = computed(() => !!props.kind && props.id !== undefined)
</script>

<template>
  <span class="group/tags flex w-full min-w-0 items-center gap-1">
    <span v-if="!tags.length" class="text-sm text-dimmed">—</span>
    <!-- Above the row's stretched link, so clicking a tag doesn't open the row -->
    <TagsChip
      v-for="tag in shown"
      :key="tag.id"
      :tag="tag"
      :selectable="selectable"
      :class="selectable ? 'relative z-1' : undefined"
      @select="emit('select', tag)"
    />
    <span
      v-if="hidden.length"
      class="shrink-0 text-xs text-muted tabular-nums"
      :title="hidden.map(tag => tag.name).join(', ')"
    >+{{ hidden.length }}</span>

    <TagsBulkMenu
      v-if="editable"
      :kind="kind!"
      :rows="[{ id: id!, tags }]"
      @changed="emit('changed')"
    >
      <button
        type="button"
        aria-label="Add a tag"
        title="Add a tag"
        class="relative z-1 flex size-5 shrink-0 cursor-pointer items-center justify-center rounded-full border border-dashed border-accented text-muted opacity-0 outline-none transition-[opacity,background-color,color] duration-150 group-hover/tags:opacity-100 hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default focus-visible:opacity-100 data-[state=open]:bg-elevated data-[state=open]:text-default data-[state=open]:opacity-100"
      >
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
      </button>
    </TagsBulkMenu>
  </span>
</template>
