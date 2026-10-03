<script setup lang="ts">
import type { DashboardActiveExperiment } from '~/types'

// Shown only while something runs or waits to: the rest of the time it takes no room.
// One experiment goes straight to it, with its progress; several go to the list.
const props = defineProps<{
  active: readonly DashboardActiveExperiment[]
}>()

const { runOf } = useLiveRuns()

const running = computed(() => props.active.filter(exp => exp.status === 'running'))
const queued = computed(() => props.active.length - running.value.length)
const first = computed(() => props.active[0])
const single = computed(() => props.active.length === 1)

const summary = computed(() => {
  const parts = []
  if (running.value.length)
    parts.push(`${running.value.length} running`)
  if (queued.value)
    parts.push(`${queued.value} queued`)
  return parts.join(' · ')
})
</script>

<template>
  <NuxtLink
    v-if="first"
    :to="single ? `/experiments/${first.id}` : '/experiments'"
    class="flex items-center gap-2.5 h-10 px-4 rounded-lg border border-info/30 bg-info/10 text-sm text-toned outline-none hover:bg-info/15 focus-visible:ring-2 focus-visible:ring-inverted"
  >
    <span
      class="size-1.5 shrink-0 rounded-full bg-info"
      :class="{ 'motion-safe:animate-pulse': running.length }"
      aria-hidden="true"
    />
    <span class="shrink-0 font-medium text-highlighted">{{ summary }}</span>
    <span class="min-w-0 truncate text-muted">
      {{ first.name }}<template v-if="!single"> and {{ active.length - 1 }} more</template>
    </span>
    <UIRunProgress v-if="single" :run="runOf(first.id)" class="ms-auto shrink-0" />
    <UIcon
      name="i-lucide-arrow-right"
      class="size-3.5 shrink-0 text-highlighted"
      :class="{ 'ms-auto': !single }"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
