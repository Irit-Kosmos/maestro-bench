<script setup lang="ts">
import type { Tag, TagWithCount } from '~/types'

// The tags of an item, by id. The chips are the current tags; the button opens a field that searches the
// shared tags and offers to create one when nothing matches (see TagsPicker).
const selected = defineModel<number[]>({ required: true })

const { tags } = useTags()

const chosen = computed(() => selected.value
  .map(id => tags.value.find(tag => tag.id === id))
  .filter((tag): tag is TagWithCount => !!tag))

function remove(id: number) {
  selected.value = selected.value.filter(other => other !== id)
}

function toggle(tag: Tag) {
  if (selected.value.includes(tag.id))
    remove(tag.id)
  else
    selected.value = [...selected.value, tag.id]
}

function add(tag: Tag) {
  if (!selected.value.includes(tag.id))
    selected.value = [...selected.value, tag.id]
}

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5">
    <TagsChip
      v-for="tag in chosen"
      :key="tag.id"
      :tag="tag"
      size="md"
      removable
      @remove="remove(tag.id)"
    />

    <UPopover :content="CONTENT" :ui="{ content: 'overflow-hidden' }">
      <button
        type="button"
        class="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-full border border-dashed border-accented px-2.5 text-sm text-muted outline-none transition-colors duration-150 hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default data-[state=open]:bg-elevated data-[state=open]:text-default"
        :aria-label="chosen.length ? 'Add a tag' : undefined"
      >
        <UIcon name="i-ph-plus-bold" class="size-3.5" aria-hidden="true" />
        <template v-if="!chosen.length">
          Add tags
        </template>
      </button>

      <template #content>
        <TagsPicker :selected="selected" @toggle="toggle" @create="add" />
      </template>
    </UPopover>
  </div>
</template>
