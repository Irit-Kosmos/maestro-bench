<script setup lang="ts">
import type { Agent, AgentTeam, Dataset, Experiment } from '~/types'

// Page meta
definePageMeta({
  title: 'Dashboard',
})

// Fetch data directly in the page
const { data: experiments, pending: experimentsPending, refresh: refreshExperiments } = await useMyLazyFetch<Experiment[]>('/experiments')
const { data: datasets, pending: datasetsPending, refresh: refreshDatasets } = await useMyLazyFetch<Dataset[]>('/datasets')
const { data: agentTeams, pending: teamsPending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')

// Composables
const { showComingSoon } = useStandardToast()

// Refresh all data
async function refresh() {
  await Promise.all([
    refreshExperiments(),
    refreshDatasets(),
    refreshTeams(),
    refreshAgents(),
  ])
}

// Computed stats
const datasetsCount = computed(() => datasets.value?.length || 0)
const agentTeamsCount = computed(() => agentTeams.value?.length || 0)
const agentsCount = computed(() => agents.value?.length || 0)
const isAdditionalStatsLoading = computed(() => datasetsPending.value || teamsPending.value || agentsPending.value)

// Recent experiments (last 10)
const recentExperiments = computed(() => {
  return experiments.value?.slice(0, 10) || []
})

// Overall loading state
const pending = computed(() => experimentsPending.value || datasetsPending.value || teamsPending.value || agentsPending.value)

// Stats computed
const stats = computed(() => ({
  totalExperiments: experiments.value?.length || 0,
  totalDatasets: datasets.value?.length || 0,
  totalAgentTeams: agentTeams.value?.length || 0,
  totalAgents: agents.value?.length || 0,
}))

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
        :value="stats.totalExperiments"
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
      action-to="/experiments/new"
      @refresh="refresh"
      @view-experiment="handleViewExperiment"
      @delete-experiment="handleDeleteExperiment"
    />
  </BasePageContent>
</template>
