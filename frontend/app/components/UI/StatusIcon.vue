<script setup lang="ts">
import type { ExperimentStatus } from '~/types'

// Each status has its own shape, so it still reads without color:
// dashed (waiting), half-filled (in progress), check, cross, slash (stopped), alert
const props = withDefaults(defineProps<{
  status?: ExperimentStatus | string | null
  /** Tailwind size class of the icon */
  size?: string
  /** Rich tooltip with the status in words, instead of the native title */
  tooltip?: boolean
}>(), {
  size: 'size-3.5',
  tooltip: false,
})

const config = computed(() => {
  switch (props.status) {
    case 'completed': return { icon: 'i-ph-check-circle-bold', class: 'text-success' }
    case 'running': return { icon: null, class: 'text-warning' }
    case 'failed': return { icon: 'i-ph-x-circle-bold', class: 'text-error' }
    case 'cancelled': return { icon: 'i-ph-prohibit-bold', class: 'text-orange-600 dark:text-orange-400' }
    case 'partial': return { icon: 'i-ph-warning-circle-bold', class: 'text-warning' }
    default: return { icon: 'i-ph-circle-dashed-bold', class: 'text-muted' }
  }
})

const details: Record<string, string> = {
  pending: 'Waiting to start',
  running: 'In progress',
  completed: 'Finished successfully',
  failed: 'Failed',
  cancelled: 'Stopped before the end',
  partial: 'Finished, some runs did not complete',
}

const status = computed(() => props.status || 'pending')

const label = computed(() => status.value.charAt(0).toUpperCase() + status.value.slice(1))

const detail = computed(() => details[status.value] ?? label.value)
</script>

<template>
  <UTooltip :text="detail" :disabled="!tooltip">
    <span class="inline-flex shrink-0 items-center align-middle" :title="tooltip ? undefined : label">
      <!-- Lucide has no half-filled circle -->
      <svg
        v-if="!config.icon"
        :class="[size, config.class]"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 6a6 6 0 0 1 0 12z" fill="currentColor" stroke="none" />
      </svg>
      <UIcon v-else :name="config.icon" :class="[size, config.class]" aria-hidden="true" />
      <span class="sr-only">{{ label }}</span>
    </span>
  </UTooltip>
</template>
