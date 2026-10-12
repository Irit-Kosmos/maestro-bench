<script setup lang="ts">
// The earlier executions of an experiment (or of a batch's experiments), as a row of small status icons next to its status.
// Nothing while there is no earlier execution.
const props = withDefaults(defineProps<{
  /** Status of the executions before the latest one, from the newest to the oldest */
  earlier?: readonly string[] | null
  /** Icons shown before the rest is counted */
  max?: number
}>(), {
  max: 4,
})

const runs = computed(() => props.earlier ?? [])

const shown = computed(() => runs.value.slice(0, props.max))

const hidden = computed(() => runs.value.length - shown.value.length)

const summary = computed(() => {
  const counts = new Map<string, number>()
  for (const run of runs.value)
    counts.set(run, (counts.get(run) ?? 0) + 1)
  return `Earlier runs: ${[...counts].map(([run, count]) => `${count} ${run}`).join(', ')}`
})
</script>

<template>
  <UTooltip v-if="runs.length" :text="summary">
    <!-- Focusable so the summary opens from the keyboard; raised above a row's stretched link so the pointer reaches it -->
    <span
      tabindex="0"
      class="relative z-1 inline-flex items-center rounded-sm text-xs text-muted tabular-nums outline-none focus-visible:ring-2 focus-visible:ring-inverted"
    >
      <!-- Shapes, not just colors, tell the runs apart; the summary says it in words. The icons' own titles stay out of the way -->
      <span class="pointer-events-none flex items-center gap-0.5" aria-hidden="true">
        <UIStatusIcon v-for="(run, index) in shown" :key="index" :status="run" size="size-3" />
      </span>
      <span v-if="hidden" class="ms-1" aria-hidden="true">+{{ hidden }}</span>
      <span class="sr-only">{{ summary }}</span>
    </span>
  </UTooltip>
</template>
