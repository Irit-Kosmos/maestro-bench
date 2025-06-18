<script setup lang="ts">
// Composables
const { recentExperiments, stats, pending, refresh } = useExperiments()
const { showNotification } = useNotifications()

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleDeleteExperiment(_id: number) {
  // TODO: Add confirmation dialog
  showNotification('Delete confirmation dialog coming soon!', 'info')
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <!-- Stats Overview -->
      <DashboardStatsOverview :stats="stats" :loading="pending" />

      <!-- Recent Experiments -->
      <ExperimentsTable
        :experiments="recentExperiments"
        :loading="pending"
        @refresh="refresh"
        @view-experiment="handleViewExperiment"
        @delete-experiment="handleDeleteExperiment"
      />
    </div>
  </div>
</template>
