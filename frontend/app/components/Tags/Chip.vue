<script setup lang="ts">
import type { Tag } from '~/types'

// A tag: its colour as a dot, then its name. Removable in the field that edits tags.
defineProps<{
  tag: Pick<Tag, 'name' | 'color'>
  removable?: boolean
}>()

const emit = defineEmits<{
  remove: []
}>()
</script>

<template>
  <span
    class="inline-flex h-5 max-w-40 shrink-0 items-center gap-1.5 rounded-full border border-default bg-elevated/40 ps-2 text-xs text-default"
    :class="removable ? 'pe-0.5' : 'pe-2'"
  >
    <span class="size-2 shrink-0 rounded-full" :class="tagDot(tag.color)" aria-hidden="true" />
    <span class="truncate" :title="tag.name">{{ tag.name }}</span>
    <button
      v-if="removable"
      type="button"
      :aria-label="`Remove tag ${tag.name}`"
      class="flex size-4 shrink-0 cursor-pointer items-center justify-center rounded-full text-dimmed outline-none transition-colors duration-150 hover:bg-accented/60 hover:text-default focus-visible:bg-accented/60 focus-visible:text-default"
      @click="emit('remove')"
    >
      <UIcon name="i-lucide-x" class="size-3" aria-hidden="true" />
    </button>
  </span>
</template>
