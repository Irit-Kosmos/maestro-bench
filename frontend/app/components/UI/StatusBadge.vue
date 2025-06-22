<script setup lang="ts">
import type { ExperimentStatus } from '~/types'

interface Props {
  status: ExperimentStatus | string
  size?: 'xs' | 'sm' | 'md' | 'lg'
  variant?: 'solid' | 'outline' | 'soft' | 'subtle'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'sm',
  variant: 'soft',
})

const { getStatusColor } = useUIHelpers()

const statusConfig = computed(() => {
  const status = props.status as ExperimentStatus
  return {
    color: getStatusColor(status),
    label: status.charAt(0).toUpperCase() + status.slice(1),
  }
})
</script>

<template>
  <UBadge
    :color="statusConfig.color"
    :variant="variant"
    :size="size"
    :label="statusConfig.label"
    class="capitalize"
  />
</template>
