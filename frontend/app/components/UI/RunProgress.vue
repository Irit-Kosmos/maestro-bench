<script setup lang="ts">
import type { RunState } from '~/types'

// Rows a running execution has processed: a bar and the count, with the failed ones named.
// Nothing once the run is over, where the figures live with the run itself
defineProps<{
  run?: RunState | null
}>()
</script>

<template>
  <div v-if="run?.status === 'running'" class="flex items-center gap-2 text-xs text-muted tabular-nums">
    <UProgress
      :model-value="run.rows_total ? run.rows_done : null"
      :max="run.rows_total || 1"
      size="xs"
      class="w-20"
      aria-label="Rows processed"
    />
    <span>{{ run.rows_done }}<template v-if="run.rows_total"> / {{ run.rows_total }}</template></span>
    <span v-if="run.rows_failed" class="text-error">{{ run.rows_failed }} failed</span>
  </div>
</template>
