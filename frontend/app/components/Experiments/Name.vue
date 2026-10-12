<script setup lang="ts">
const props = defineProps<{
  name: string
  batchName?: string | null
  stacked?: boolean
  /** Muted text after the name, e.g. an id; stacked, it stays on the name's line */
  hint?: string
}>()

const parts = computed(() => splitExperimentName(props.name, props.batchName))
const title = computed(() => parts.value.batch ? props.name : undefined)
const rest = computed(() => parts.value.segments.slice(1))
</script>

<template>
  <span v-if="stacked" class="flex min-h-9 min-w-0 flex-col justify-center" :title="title">
    <span class="flex min-w-0 items-baseline gap-2 leading-5">
      <span class="truncate">{{ parts.segments[0] }}</span>
      <span v-if="hint" class="shrink-0 text-xs font-normal text-muted tabular-nums">{{ hint }}</span>
      <slot name="after" />
    </span>
    <span v-if="rest.length" class="truncate text-xs font-normal leading-4 text-muted">{{ rest.join(' · ') }}</span>
    <span v-if="parts.batch" class="sr-only"> in batch {{ parts.batch }}</span>
  </span>

  <span v-else class="truncate" :title="title">
    <template v-for="(segment, i) in parts.segments" :key="i">
      <span v-if="i > 0" class="font-normal text-dimmed" aria-hidden="true"> · </span>
      <span :class="i > 0 && 'font-normal text-toned'">{{ segment }}</span>
    </template>
    <span v-if="parts.batch" class="sr-only"> in batch {{ parts.batch }}</span>
  </span>
</template>
