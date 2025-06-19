<script setup lang="ts">
import type { ExperimentStats } from '~/types'

interface Props {
  stats: ExperimentStats
  loading?: boolean
}

defineProps<Props>()
</script>

<template>
  <DashboardStatsCard
    title="Total Experiments"
    :value="stats.total"
    icon="i-lucide:activity"
    icon-color="text-blue-600"
    :loading="loading"
  />
</template>
