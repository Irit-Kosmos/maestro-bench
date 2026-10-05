<script setup lang="ts">
import type { ExperimentStatus } from '~/types'

// Each status has its own shape, so it still reads without color:
// dashed (not started), clock (queued), half-filled (in progress), check, cross, slash (stopped), pause (interrupted), alert
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
    case 'queued': return { icon: 'i-ph-clock-bold', class: 'text-muted' }
    case 'interrupted': return { icon: 'i-ph-pause-circle-bold', class: 'text-orange-600 dark:text-orange-400' }
    case 'cancelled': return { icon: 'i-ph-prohibit-bold', class: 'text-orange-600 dark:text-orange-400' }
    case 'partial': return { icon: 'i-ph-warning-circle-bold', class: 'text-warning' }
    default: return { icon: 'i-ph-circle-dashed-bold', class: 'text-muted' }
  }
})

const details: Record<string, string> = {
  pending: 'Waiting to start',
  queued: 'Waiting for a free slot',
  running: 'In progress',
  completed: 'Finished successfully',
  failed: 'Failed',
  cancelled: 'Stopped before the end',
  interrupted: 'Cut short by a server restart',
  partial: 'Finished, some runs did not complete',
}

const status = computed(() => props.status || 'pending')

const label = computed(() => status.value.charAt(0).toUpperCase() + status.value.slice(1))

const detail = computed(() => details[status.value] ?? label.value)
</script>

<template>
  <UTooltip :text="detail" :disabled="!tooltip">
    <span class="inline-flex shrink-0 items-center align-middle" :title="tooltip ? undefined : label">
      <!-- A status that changes while it is on screen (a run ending) crosses over to the next one -->
      <Transition name="status-swap" mode="out-in">
        <!-- Lucide has no half-filled circle -->
        <svg
          v-if="!config.icon"
          :key="status"
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
        <UIcon v-else :key="status" :name="config.icon" :class="[size, config.class]" aria-hidden="true" />
      </Transition>
      <span class="sr-only">{{ label }}</span>
    </span>
  </UTooltip>
</template>

<style scoped>
/* Same swap as the copy button. No `appear`: a row that mounts (or scrolls in) never plays it */
.status-swap-enter-active {
  transition: opacity 200ms var(--ease-out), scale 200ms var(--ease-out), filter 200ms var(--ease-out);
}

.status-swap-leave-active {
  transition: opacity 100ms var(--ease-out), scale 100ms var(--ease-out), filter 100ms var(--ease-out);
}

.status-swap-enter-from,
.status-swap-leave-to {
  opacity: 0;
  scale: 0.25;
  filter: blur(4px);
}

/* Reduced motion keeps the swap, drops the movement */
@media (prefers-reduced-motion: reduce) {
  .status-swap-enter-active,
  .status-swap-leave-active {
    transition: opacity 150ms ease;
  }

  .status-swap-enter-from,
  .status-swap-leave-to {
    scale: 1;
    filter: none;
  }
}
</style>
