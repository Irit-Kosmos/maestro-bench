<script setup lang="ts">
import type { Tag } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// The tags of the selected rows of a list. A tag every row has is checked, one only some have is dashed;
// clicking it puts it on every row, or takes it off every row when they all have it already.
const props = defineProps<{
  kind: 'prompt' | 'analysis'
  rows: { id: number, tags: Tag[] }[]
}>()

const emit = defineEmits<{
  /** The tags of the rows changed: the list should be read again */
  changed: []
}>()

const { assignTags } = useTags()
const toast = useToast()

const coverage = computed(() => tagCoverage(props.rows))
function ids(everyRow: boolean) {
  return [...coverage.value]
    .filter(([, count]) => everyRow ? count === props.rows.length : count < props.rows.length)
    .map(([id]) => id)
}
const onEvery = computed(() => ids(true))
const onSome = computed(() => ids(false))

async function apply(change: { add?: number[], remove?: number[] }) {
  try {
    await assignTags(props.kind, props.rows.map(row => row.id), change)
    emit('changed')
  }
  catch (error) {
    toast.add({ title: 'Error', description: apiErrorMessage(error) ?? 'Failed to update the tags', color: 'error', icon: 'i-lucide:alert-circle' })
  }
}

function toggle(tag: Tag) {
  return apply(onEvery.value.includes(tag.id) ? { remove: [tag.id] } : { add: [tag.id] })
}

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <UPopover :content="CONTENT" :ui="{ content: 'overflow-hidden' }">
    <UButton
      variant="ghost"
      color="neutral"
      icon="i-lucide-tag"
      size="sm"
    >
      Tags
    </UButton>

    <template #content>
      <TagsPicker
        :selected="onEvery"
        :partial="onSome"
        @toggle="toggle"
        @create="tag => apply({ add: [tag.id] })"
      />
    </template>
  </UPopover>
</template>
