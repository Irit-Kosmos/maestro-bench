<script setup lang="ts">
import type { ExperimentStatus } from '~/types'

// Each status has its own shape, so it still reads without color
const props = defineProps<{
  status?: ExperimentStatus | string | null
}>()

const config = computed(() => {
  switch (props.status) {
    case 'completed': return { icon: 'i-lucide-circle-check', class: 'text-success' }
    case 'running': return { icon: 'i-lucide-loader-circle', class: 'text-info motion-safe:animate-spin' }
    case 'failed': return { icon: 'i-lucide-circle-x', class: 'text-error' }
    default: return { icon: 'i-lucide-circle-dashed', class: 'text-warning' }
  }
})

const label = computed(() => {
  const status = props.status || 'pending'
  return status.charAt(0).toUpperCase() + status.slice(1)
})
</script>

<template>
  <span class="inline-flex shrink-0" :title="label">
    <UIcon :name="config.icon" class="size-3.5" :class="config.class" aria-hidden="true" />
    <span class="sr-only">{{ label }}</span>
  </span>
</template>
