<script setup lang="ts">
// The earlier executions of an experiment (or of a batch's experiments), as a stack of dots next to its status.
// Nothing while there is no earlier execution.
const props = withDefaults(defineProps<{
  /** Status of the executions before the latest one, from the newest to the oldest */
  earlier?: readonly string[] | null
  /** Dots shown before the rest is counted */
  max?: number
}>(), {
  max: 4,
})

const COLORS: Record<string, string> = {
  completed: 'bg-success',
  running: 'bg-warning',
  partial: 'bg-warning',
  failed: 'bg-error',
  cancelled: 'bg-orange-600 dark:bg-orange-400',
}

const FALLBACK = 'bg-neutral-400 dark:bg-neutral-500'

const runs = computed(() => props.earlier ?? [])

const dots = computed(() => runs.value.slice(0, props.max))

const hidden = computed(() => runs.value.length - dots.value.length)

const summary = computed(() => {
  const counts = new Map<string, number>()
  for (const run of runs.value)
    counts.set(run, (counts.get(run) ?? 0) + 1)
  return `Earlier runs: ${[...counts].map(([run, count]) => `${count} ${run}`).join(', ')}`
})
</script>

<template>
  <UTooltip v-if="runs.length" :text="summary">
    <span class="inline-flex items-center text-xs text-muted tabular-nums">
      <span class="flex items-center -space-x-1" aria-hidden="true">
        <span
          v-for="(run, index) in dots"
          :key="index"
          class="size-2.5 rounded-full ring-2 ring-(--ui-bg) dark:ring-default"
          :class="COLORS[run] ?? FALLBACK"
        />
      </span>
      <span v-if="hidden" class="ml-1" aria-hidden="true">+{{ hidden }}</span>
      <span class="sr-only">{{ summary }}</span>
    </span>
  </UTooltip>
</template>
