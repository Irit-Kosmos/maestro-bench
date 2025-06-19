<script setup lang="ts">
import type { AgentExecutionConfig, Experiment, ExperimentExecution } from '~/types'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { fetchExperiment, deleteExperiment } = useExperiments()
const { fetchExperimentExecutions } = useExperimentExecutions()
const { formatDuration } = useUIHelpers()

// State
const experiment = ref<Experiment | null>(null)
const executions = ref<ExperimentExecution[]>([])
const loading = ref(true)
const showDeleteDialog = ref(false)
const isDeleting = ref(false)

// Computed
const pageTitle = computed(() => {
  return experiment.value ? experiment.value.name : 'Loading...'
})

// Set page title and meta
useSeoMeta({
  title: pageTitle,
  description: computed(() =>
    experiment.value
      ? `View details and configuration for experiment: ${experiment.value.name}`
      : 'Loading experiment...',
  ),
})

const statusColor = computed(() => {
  if (!experiment.value)
    return 'neutral'
  switch (experiment.value.status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'error'
    case 'pending': return 'warning'
    default: return 'neutral'
  }
})

// Latest execution for configuration display
const latestExecution = computed(() => {
  if (!executions.value || executions.value.length === 0)
    return null
  return [...executions.value].sort((a, b) =>
    new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  )[0]
})

// Configuration accordion items
const configurationItems = computed(() => {
  if (!latestExecution.value || !latestExecution.value.agent_executions)
    return []

  return latestExecution.value.agent_executions.map((agentConfig: AgentExecutionConfig) => ({
    label: agentConfig.agent_name_snapshot,
    icon: 'i-lucide-user',
    value: `agent-${agentConfig.id}`,
    slot: `agent-${agentConfig.id}`,
    agentConfig,
  }))
})

// Parse dataset snapshot
const datasetInfo = computed(() => {
  if (!latestExecution.value)
    return null
  try {
    return JSON.parse(latestExecution.value.dataset_snapshot)
  }
  catch {
    return null
  }
})

// Methods
async function loadExperiment() {
  loading.value = true
  try {
    const result = await fetchExperiment(experimentId.value)
    if (result.success && result.data) {
      experiment.value = result.data as Experiment
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Experiment not found',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
      await navigateTo('/experiments')
      return
    }

    // Load executions for configuration data
    const executionsResult = await fetchExperimentExecutions(experimentId.value)
    if (executionsResult.success && executionsResult.data) {
      executions.value = executionsResult.data
    }
  }
  catch (error) {
    console.error('Error loading experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load experiment',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
    await navigateTo('/experiments')
  }
  finally {
    loading.value = false
  }
}

async function handleDeleteExperiment() {
  if (!experiment.value)
    return

  isDeleting.value = true
  try {
    const result = await deleteExperiment(experiment.value.id)
    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Experiment deleted successfully',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      await navigateTo('/experiments')
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to delete experiment',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch (error) {
    console.error('Error deleting experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to delete experiment',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    isDeleting.value = false
    showDeleteDialog.value = false
  }
}

const duration = computed(() => {
  return experiment.value
    ? formatDuration(
        experiment.value.completed_at
          ? new Date(experiment.value.completed_at).getTime() / 1000
          - new Date(experiment.value.created_at).getTime() / 1000
          : 0,
      )
    : 'N/A'
})

// Helper function to format variables JSON
function formatVariables(variables: string | null): string {
  if (!variables)
    return 'None'
  try {
    return JSON.stringify(JSON.parse(variables), null, 2)
  }
  catch {
    return variables
  }
}

// Lifecycle
onMounted(() => {
  loadExperiment()
})

// Watch for route changes
watch(() => route.params.id, () => {
  loadExperiment()
})
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
      </div>

      <!-- Experiment Details -->
      <div v-else-if="experiment" class="space-y-8">
        <!-- Header with Actions -->
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-2xl font-bold text-gray-900">
              {{ experiment.name }}
            </h1>
            <p class="text-gray-500 mt-1">
              Experiment ID: {{ experiment.id }}
            </p>
          </div>
          <div class="flex gap-3">
            <UButton
              variant="outline"
              color="neutral"
              icon="i-lucide:arrow-left"
              @click="$router.go(-1)"
            >
              Back
            </UButton>
            <UButton
              variant="outline"
              color="error"
              icon="i-lucide:trash-2"
              @click="showDeleteDialog = true"
            >
              Delete
            </UButton>
          </div>
        </div>

        <!-- Overview Card -->
        <UCard>
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <UIcon name="i-lucide:flask-conical" class="h-6 w-6" />
                <h2 class="text-xl font-semibold text-gray-900">
                  Experiment Overview
                </h2>
              </div>
              <UBadge
                :color="statusColor"
                variant="subtle"
                class="capitalize"
              >
                {{ experiment.status }}
              </UBadge>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Created
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                {{ new Date(experiment.created_at).toLocaleDateString() }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Dataset
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                {{ experiment.dataset?.name || 'Unknown' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Executions
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                {{ executions.length }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Duration
              </dt>
              <dd class="text-lg font-semibold text-gray-900">
                {{ experiment.status === 'completed' ? duration : '-' }}
              </dd>
            </div>
          </div>
        </UCard>

        <!-- Dataset Configuration -->
        <UCard v-if="datasetInfo">
          <template #header>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-database" class="h-6 w-6" />
              <h2 class="text-xl font-semibold text-gray-900">
                Dataset Configuration
              </h2>
            </div>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Name
              </dt>
              <dd class="text-sm text-gray-900">
                {{ datasetInfo.name }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                File Path
              </dt>
              <dd class="text-sm text-gray-900 font-mono">
                {{ datasetInfo.file_path }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500 mb-2">
                Description
              </dt>
              <dd class="text-sm text-gray-900">
                {{ datasetInfo.description || 'No description' }}
              </dd>
            </div>
          </div>
        </UCard>

        <!-- Agent Configurations -->
        <UCard v-if="latestExecution && latestExecution.agent_executions.length > 0">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <UIcon name="i-lucide-users" class="h-6 w-6" />
                <h2 class="text-xl font-semibold text-gray-900">
                  Agent Configurations
                </h2>
              </div>
              <UBadge
                :label="`${latestExecution.agent_executions.length} agents`"
                color="info"
                variant="soft"
              />
            </div>
          </template>

          <UAccordion
            type="multiple"
            :items="configurationItems"
            class="space-y-0"
          >
            <template
              v-for="agentConfig in latestExecution.agent_executions"
              :key="agentConfig.id"
              #[`agent-${agentConfig.id}`]
            >
              <div class="space-y-6 pb-4">
                <!-- Agent Basic Info -->
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <dt class="text-sm font-medium text-gray-500 mb-1">
                      Agent Name
                    </dt>
                    <dd class="text-sm text-gray-900">
                      {{ agentConfig.agent_name_snapshot }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-gray-500 mb-1">
                      Team
                    </dt>
                    <dd class="text-sm text-gray-900">
                      {{ agentConfig.agent_team_name_snapshot }}
                    </dd>
                  </div>
                </div>

                <!-- System Prompt -->
                <div v-if="agentConfig.final_system_prompt">
                  <dt class="text-sm font-medium text-gray-500 mb-2">
                    System Prompt
                  </dt>
                  <dd class="bg-gray-50 rounded-lg p-4 text-sm text-gray-900 whitespace-pre-wrap">
                    {{ agentConfig.final_system_prompt }}
                  </dd>
                </div>

                <!-- User Prompt -->
                <div v-if="agentConfig.final_user_prompt">
                  <dt class="text-sm font-medium text-gray-500 mb-2">
                    User Prompt
                  </dt>
                  <dd class="bg-gray-50 rounded-lg p-4 text-sm text-gray-900 whitespace-pre-wrap">
                    {{ agentConfig.final_user_prompt }}
                  </dd>
                </div>

                <!-- Variables -->
                <div v-if="agentConfig.final_variables">
                  <dt class="text-sm font-medium text-gray-500 mb-2">
                    Variables
                  </dt>
                  <dd class="bg-gray-50 rounded-lg p-4 text-sm text-gray-900">
                    <pre class="whitespace-pre-wrap font-mono">{{ formatVariables(agentConfig.final_variables) }}</pre>
                  </dd>
                </div>

                <!-- Configuration Metadata -->
                <div class="border-t pt-4">
                  <dt class="text-sm font-medium text-gray-500 mb-2">
                    Configuration Snapshot
                  </dt>
                  <div class="text-xs text-gray-600 space-y-1">
                    <div>Agent ID: {{ agentConfig.agent_id }}</div>
                    <div>Team ID: {{ agentConfig.agent_team_id_snapshot }}</div>
                    <div>Created: {{ new Date(agentConfig.created_at).toLocaleString() }}</div>
                  </div>
                </div>
              </div>
            </template>
          </UAccordion>
        </UCard>

        <!-- No Configuration Available -->
        <UCard v-else>
          <div class="text-center py-12">
            <UIcon name="i-lucide-settings" class="mx-auto h-16 w-16 text-gray-400 mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              No Configuration Available
            </h3>
            <p class="text-gray-600">
              No execution configuration found for this experiment.
            </p>
          </div>
        </UCard>

        <!-- Experiment Description -->
        <UCard v-if="experiment.description">
          <template #header>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-file-text" class="h-6 w-6" />
              <h2 class="text-xl font-semibold text-gray-900">
                Description
              </h2>
            </div>
          </template>

          <div class="prose prose-sm max-w-none">
            <p class="text-gray-700 whitespace-pre-wrap">
              {{ experiment.description }}
            </p>
          </div>
        </UCard>
      </div>

      <!-- Error State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          Experiment Not Found
        </h3>
        <p class="text-gray-500 mb-4">
          The experiment you're looking for doesn't exist.
        </p>
        <UButton to="/" variant="solid" color="primary">
          Return to Dashboard
        </UButton>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteDialog" title="Delete Experiment">
      <template #body>
        <p class="text-gray-600">
          Are you sure you want to delete "{{ experiment?.name }}"? This action cannot be undone.
        </p>
      </template>

      <template #footer>
        <div class="flex gap-3 justify-end">
          <UButton
            variant="outline"
            color="neutral"
            @click="showDeleteDialog = false"
          >
            Cancel
          </UButton>
          <UButton
            variant="solid"
            color="error"
            :loading="isDeleting"
            @click="handleDeleteExperiment"
          >
            Delete
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
