<script setup lang="ts">
// Rows an execution processed.
// - "warn" (analyses): small samples get a warning badge, icon and tooltip, since their metrics mislead
// - "quiet" (lists): small samples recede, real runs stand out
const props = withDefaults(defineProps<{
  rows?: number | null
  size?: 'xs' | 'sm' | 'md'
  tone?: 'warn' | 'quiet'
}>(), {
  rows: null,
  size: 'sm',
  tone: 'warn',
})

const small = computed(() => isSmallSample(props.rows))
const tooltip = computed(() =>
  props.rows == null ? '' : `Small sample: metrics from ${formatRows(props.rows)} aren’t reliable (under ${SMALL_SAMPLE_ROWS})`,
)
</script>

<template>
  <span v-if="rows === null || rows === undefined" class="text-dimmed">—</span>

  <UTooltip v-else-if="small && tone === 'warn'" :text="tooltip">
    <UBadge
      color="warning"
      variant="soft"
      :size="size"
      icon="i-ph-warning-bold"
      class="tabular-nums"
    >
      {{ formatRows(rows) }}<span class="sr-only">, small sample</span>
    </UBadge>
  </UTooltip>

  <span
    v-else
    class="tabular-nums"
    :class="small ? 'text-muted' : 'font-medium text-highlighted'"
    :title="small ? tooltip : undefined"
  >
    {{ formatRows(rows) }}
  </span>
</template>
