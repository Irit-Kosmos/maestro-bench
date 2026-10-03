<script setup lang="ts">
import type { Tag } from '~/types'

// A tag: its colour as a dot, then its name. Removable in the field that edits tags.
// Small in tables and headers, medium where tags are edited. `selectable` makes it a button, e.g. to filter a list.
withDefaults(defineProps<{
  tag: Pick<Tag, 'name' | 'color'>
  removable?: boolean
  selectable?: boolean
  size?: 'sm' | 'md'
}>(), {
  size: 'sm',
})

const emit = defineEmits<{
  remove: []
  select: []
}>()
</script>

<template>
  <component
    :is="selectable ? 'button' : 'span'"
    :type="selectable ? 'button' : undefined"
    :title="selectable ? `Filter by ${tag.name}` : undefined"
    class="inline-flex shrink-0 items-center rounded-full border border-default bg-elevated/40 text-default"
    :class="[
      selectable ? 'cursor-pointer outline-none transition-colors duration-150 hover:bg-accented/50 focus-visible:ring-2 focus-visible:ring-inverted' : undefined,
      size === 'md' ? 'h-7 max-w-56 gap-2 ps-2.5 text-sm' : 'h-5 max-w-40 gap-1.5 ps-2 text-xs',
      removable ? 'pe-1' : size === 'md' ? 'pe-2.5' : 'pe-2',
    ]"
    @click="selectable && emit('select')"
  >
    <span class="shrink-0 rounded-full" :class="[tagDot(tag.color), size === 'md' ? 'size-2.5' : 'size-2']" aria-hidden="true" />
    <span class="truncate" :title="selectable ? undefined : tag.name">{{ tag.name }}</span>
    <button
      v-if="removable"
      type="button"
      :aria-label="`Remove tag ${tag.name}`"
      class="flex shrink-0 cursor-pointer items-center justify-center rounded-full text-dimmed outline-none transition-colors duration-150 hover:bg-accented/60 hover:text-default focus-visible:bg-accented/60 focus-visible:text-default"
      :class="size === 'md' ? 'size-5' : 'size-4'"
      @click="emit('remove')"
    >
      <UIcon name="i-ph-x-bold" :class="size === 'md' ? 'size-3.5' : 'size-3'" aria-hidden="true" />
    </button>
  </component>
</template>
