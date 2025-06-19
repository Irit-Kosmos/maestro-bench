<script setup lang="ts">
// Composables
const { recentExperiments, stats, pending, refresh } = useExperiments()
const { datasets, pending: datasetsPending } = useDatasets()
const { agentTeams, pending: teamsPending } = useAgentTeams()
const { agents, pending: agentsPending } = useAgents()
const toast = useToast()

// Computed stats
const datasetsCount = computed(() => datasets.value?.length || 0)
const agentTeamsCount = computed(() => agentTeams.value?.length || 0)
const agentsCount = computed(() => agents.value?.length || 0)
const isAdditionalStatsLoading = computed(() => datasetsPending.value || teamsPending.value || agentsPending.value)

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleDeleteExperiment(_id: number) {
  // TODO: Add confirmation dialog
  toast.add({
    title: 'Coming Soon',
    description: 'Delete confirmation dialog coming soon!',
    color: 'info',
    icon: 'i-lucide:info',
  })
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <!-- Stats Overview -->
      <div class="flex flex-wrap gap-4">
        <!-- Total Experiments -->
        <DashboardStatsCard
          title="Total Experiments"
          :value="stats.total"
          icon="i-lucide:activity"
          icon-color="text-blue-600"
          :loading="pending"
        />

        <!-- Datasets Count -->
        <DashboardStatsCard
          title="Total Datasets"
          :value="datasetsCount"
          icon="i-lucide:database"
          icon-color="text-purple-600"
          :loading="isAdditionalStatsLoading"
        />

        <!-- Agent Teams & Agents Count -->
        <DashboardStatsCard
          title="Teams & Agents"
          :value="`${agentTeamsCount} teams, ${agentsCount} agents`"
          icon="i-lucide:users"
          icon-color="text-green-600"
          :loading="isAdditionalStatsLoading"
        />
      </div>

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
