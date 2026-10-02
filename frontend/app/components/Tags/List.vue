<script setup lang="ts">
import type { Tag } from '~/types'

// The tags of a row, on one line: the first few, then how many more there are.
// `selectable` makes each tag a button that says which one was clicked.
const props = withDefaults(defineProps<{
  tags: Tag[]
  max?: number
  selectable?: boolean
}>(), {
  max: 3,
})

const emit = defineEmits<{
  select: [tag: Tag]
}>()

const shown = computed(() => props.tags.slice(0, props.max))
const hidden = computed(() => props.tags.slice(props.max))
</script>

<template>
  <span v-if="!tags.length" class="text-sm text-dimmed">—</span>
  <span v-else class="flex min-w-0 items-center gap-1">
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
  </span>
</template>
