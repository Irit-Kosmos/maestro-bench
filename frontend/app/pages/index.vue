<script setup lang="ts">
// Page meta
definePageMeta({
  title: 'Dashboard',
})

// Composables
const { recentExperiments, stats, pending, refresh } = useExperiments()
const { datasets, pending: datasetsPending } = useDatasets()
const { agentTeams, pending: teamsPending } = useAgentTeams()
const { agents, pending: agentsPending } = useAgents()
const { showComingSoon } = useStandardToast()

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
  showComingSoon('Delete confirmation dialog')
}
</script>

<template>
  <BasePageContent
    title="Dashboard"
    subtitle="Overview of your experiments and resources"
    :loading="pending"
  >
    <!-- Stats Overview -->
    <div class="flex flex-wrap gap-4 mb-8">
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
      :experiments="recentExperiments || []"
      :loading="pending"
      :action-to="'/experiments/new'"
      @refresh="refresh"
      @view-experiment="handleViewExperiment"
      @delete-experiment="handleDeleteExperiment"
    />
  </BasePageContent>
</template>
