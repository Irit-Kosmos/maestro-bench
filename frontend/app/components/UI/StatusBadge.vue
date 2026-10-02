<script setup lang="ts">
import type { ExperimentStatus } from '~/types'

// A status as it reads in tables and lists: the same icon as the page titles, the word in a tooltip
defineProps<{
  status: ExperimentStatus | string
}>()
</script>

<template>
  <UIStatusIcon :status="status" size="size-4" tooltip />
</template>
