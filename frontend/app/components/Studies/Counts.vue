<script setup lang="ts">
// What a study gathers as icon + figure per kind; the kinds it has none of are left out
const props = defineProps<{
  counts: { experiments: number, batches: number, analyses: number }
}>()

const parts = computed(() => [
  { kind: 'experiment' as const, count: props.counts.experiments },
  { kind: 'batch' as const, count: props.counts.batches },
  { kind: 'analysis' as const, count: props.counts.analyses },
].filter(part => part.count > 0))

function describe(kind: 'experiment' | 'batch' | 'analysis', count: number): string {
  const meta = ITEM_KINDS[kind]
  return `${count} ${count === 1 ? meta.label : meta.plural}`.toLowerCase()
}
</script>

<template>
  <span v-if="parts.length" class="inline-flex items-center gap-3 text-sm text-toned">
    <!-- The tooltips of the app share a skip delay: once one is open, the next opens at once -->
    <UTooltip v-for="part in parts" :key="part.kind" :text="describe(part.kind, part.count)">
      <span class="inline-flex items-center gap-1">
        <UIcon :name="ITEM_KINDS[part.kind].icon" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="tabular-nums">{{ part.count }}</span>
        <span class="sr-only">{{ describe(part.kind, part.count) }}</span>
      </span>
    </UTooltip>
  </span>
  <UTooltip v-else text="Nothing in this study yet">
    <span class="text-sm text-dimmed">—<span class="sr-only">Empty</span></span>
  </UTooltip>
</template>
