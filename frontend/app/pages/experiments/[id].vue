<script setup lang="ts">
import type { AgentExecutionSnapshot, Experiment, ExperimentExecution } from '~/types'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { fetchExperiment, deleteExperiment, rerunExperiment } = useExperiments()
const { fetchExperimentExecutions } = useExperimentExecutions()
const { formatDuration } = useUIHelpers()
const { downloadResults: downloadResultsFile } = useResultsDownload()

// State
const experiment = ref<Experiment | null>(null)
const executions = ref<ExperimentExecution[]>([])
const loading = ref(true)
const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const isRerunning = ref(false)

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

  return latestExecution.value.agent_executions.map((agentConfig: AgentExecutionSnapshot) => ({
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

async function handleRerunExperiment() {
  if (!experiment.value)
    return

  isRerunning.value = true
  try {
    const result = await rerunExperiment(experiment.value.id)
    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Experiment re-run started successfully! A new execution has been created.',
        color: 'success',
        icon: 'i-lucide:play',
      })

      // Refresh the experiment and executions to show the new execution
      await loadExperiment()

      // Update the experiment status to running
      if (experiment.value) {
        experiment.value.status = 'running'
      }
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to start experiment re-run',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch (error) {
    console.error('Error re-running experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to start experiment re-run',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }
  finally {
    isRerunning.value = false
  }
}

const duration = computed(() => {
  if (!experiment.value || !executions.value.length) {
    return 'N/A'
  }

  // Get all completed executions
  const completedExecutions = executions.value.filter(
    execution => execution.status === 'completed' && execution.completed_at && execution.started_at,
  )

  if (completedExecutions.length === 0) {
    return '-'
  }

  // Calculate duration for each completed execution
  const durations = completedExecutions.map((execution) => {
    const startTime = new Date(execution.started_at).getTime() / 1000
    const endTime = new Date(execution.completed_at!).getTime() / 1000
    return endTime - startTime
  })

  // Calculate average duration
  const averageDuration = durations.reduce((sum, duration) => sum + duration, 0) / durations.length

  return formatDuration(averageDuration)
})

// Get unique models used in the experiment
const uniqueModels = computed(() => {
  if (!latestExecution.value?.agent_executions)
    return []

  const modelMap = new Map()
  latestExecution.value.agent_executions.forEach((agent) => {
    const key = `${agent.model_provider_snapshot}:${agent.model_name_snapshot}`
    if (!modelMap.has(key)) {
      modelMap.set(key, {
        name: agent.model_name_snapshot,
        provider: agent.model_provider_snapshot,
        count: 0,
      })
    }
    modelMap.get(key).count++
  })

  return Array.from(modelMap.values())
})

// Get unique prompts used in the experiment
const uniquePrompts = computed(() => {
  if (!latestExecution.value?.agent_executions)
    return []

  const promptMap = new Map()
  latestExecution.value.agent_executions.forEach((agent) => {
    const key = `${agent.prompt_name_snapshot}:${agent.prompt_version_snapshot}`
    if (!promptMap.has(key)) {
      promptMap.set(key, {
        name: agent.prompt_name_snapshot,
        version: agent.prompt_version_snapshot,
        count: 0,
      })
    }
    promptMap.get(key).count++
  })

  return Array.from(promptMap.values())
})

// Download results
async function downloadResults() {
  if (!latestExecution.value?.id) {
    toast.add({
      title: 'Error',
      description: 'No execution available to download results from',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
    return
  }

  await downloadResultsFile(latestExecution.value.id)
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
    <div class="pb-6">
      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
      </div>

      <!-- Experiment Details -->
      <div v-else-if="experiment" class="space-y-4">
        <!-- Header with Actions -->
        <div class="flex justify-between items-center">
          <div>
            <h1 class="text-2xl font-bold text-neutral-900">
              {{ experiment.name }}
            </h1>
            <p class="text-neutral-500 mt-1">
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
            <UTooltip text="Create a new execution with the same configuration">
              <UButton
                variant="outline"
                color="primary"
                icon="i-lucide:play"
                :loading="isRerunning"
                :disabled="!experiment || experiment.status === 'running'"
                @click="handleRerunExperiment"
              >
                {{ experiment?.status === 'running' ? 'Running...' : 'Re-run' }}
              </UButton>
            </UTooltip>
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
                <h2 class="text-xl font-semibold text-neutral-900">
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

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
            <div>
              <dt class="text-sm font-medium text-neutral-500 mb-2">
                Created
              </dt>
              <dd class="text-lg font-semibold text-neutral-900">
                {{ new Date(experiment.created_at).toLocaleDateString() }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500 mb-2">
                Dataset
              </dt>
              <dd class="text-lg font-semibold text-neutral-900">
                {{ experiment.dataset?.name || 'Unknown' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500 mb-2">
                Executions
              </dt>
              <dd class="text-lg font-semibold text-neutral-900">
                {{ executions.length }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500 mb-2">
                Agents
              </dt>
              <dd class="text-lg font-semibold text-neutral-900">
                {{ latestExecution?.agent_executions?.length || 0 }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500 mb-2">
                Duration
              </dt>
              <dd class="text-lg font-semibold text-neutral-900">
                {{ duration }}
              </dd>
              <div v-if="executions.length > 1" class="text-xs text-neutral-500 mt-1">
                {{ executions.filter(e => e.status === 'completed').length > 1 ? 'Average of' : 'Single' }}
                {{ executions.filter(e => e.status === 'completed').length }}
                {{ executions.filter(e => e.status === 'completed').length === 1 ? 'execution' : 'executions' }}
              </div>
            </div>
          </div>
          <!-- V2 Metrics: Tokens, Cost, Scores -->
          <div v-if="latestExecution?.total_tokens || latestExecution?.total_cost_usd || latestExecution?.scores_summary" class="mt-6 pt-6 border-t border-neutral-200">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div v-if="latestExecution.total_tokens">
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  Total Tokens
                </dt>
                <dd class="text-lg font-semibold text-neutral-900">
                  {{ latestExecution.total_tokens.toLocaleString() }}
                </dd>
              </div>
              <div v-if="latestExecution.total_cost_usd !== undefined && latestExecution.total_cost_usd !== null">
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  Total Cost
                </dt>
                <dd class="text-lg font-semibold text-neutral-900">
                  ${{ latestExecution.total_cost_usd.toFixed(4) }}
                </dd>
              </div>
              <div v-if="latestExecution.scores_summary && Object.keys(latestExecution.scores_summary).length > 0">
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  Scores
                </dt>
                <dd class="space-y-1">
                  <div
                    v-for="(score, scorer) in latestExecution.scores_summary"
                    :key="scorer"
                    class="flex items-center justify-between"
                  >
                    <span class="text-sm text-neutral-700 capitalize">{{ scorer }}</span>
                    <UBadge :label="typeof score === 'number' ? score.toFixed(3) : String(score)" color="primary" variant="subtle" />
                  </div>
                </dd>
              </div>
            </div>
          </div>

          <!-- Results File Info -->
          <div v-if="latestExecution?.results_file_path" class="mt-6 pt-6 border-t border-neutral-200">
            <div class="flex items-center justify-between">
              <div>
                <dt class="text-sm font-medium text-neutral-500 mb-1">
                  Results File
                </dt>
                <dd class="text-sm text-neutral-900 font-mono">
                  {{ latestExecution.results_file_path }}
                </dd>
              </div>
              <UButton
                variant="outline"
                color="neutral"
                icon="i-lucide-download"
                size="sm"
                :disabled="!latestExecution.results_file_path"
                @click="downloadResults"
              >
                Download Results
              </UButton>
            </div>
          </div>
        </UCard>

        <!-- Dataset Configuration -->
        <UCard v-if="datasetInfo">
          <template #header>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-database" class="h-6 w-6" />
              <h2 class="text-xl font-semibold text-neutral-900">
                Dataset Configuration
              </h2>
            </div>
          </template>

          <div class="space-y-6">
            <!-- Basic Dataset Info -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div>
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  Name
                </dt>
                <dd class="text-sm text-neutral-900">
                  {{ datasetInfo.name }}
                </dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  File Path
                </dt>
                <dd class="text-sm text-neutral-900 font-mono">
                  {{ datasetInfo.file_path }}
                </dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-neutral-500 mb-2">
                  Description
                </dt>
                <dd class="text-sm text-neutral-900">
                  {{ datasetInfo.description || 'No description' }}
                </dd>
              </div>
            </div>

            <USeparator />

            <!-- Sampling Configuration -->
            <div v-if="experiment.sampling_type && experiment.sampling_type !== 'all'">
              <div class="flex items-center gap-2 mb-4">
                <UIcon name="i-lucide-filter" class="h-5 w-5 text-primary-500" />
                <h3 class="text-base font-semibold text-neutral-900">
                  Dataset Sampling
                </h3>
              </div>

              <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div>
                  <dt class="text-sm font-medium text-neutral-500 mb-2">
                    Sampling Method
                  </dt>
                  <dd class="flex items-center gap-2">
                    <UBadge
                      :label="experiment.sampling_type === 'random' ? 'Random Sample' : 'Row Range'"
                      :color="experiment.sampling_type === 'random' ? 'info' : 'success'"
                      variant="subtle"
                    />
                  </dd>
                </div>

                <div v-if="experiment.sampling_type === 'random' && experiment.sampling_size">
                  <dt class="text-sm font-medium text-neutral-500 mb-2">
                    Sample Size
                  </dt>
                  <dd class="text-sm text-neutral-900 font-semibold">
                    {{ experiment.sampling_size }} rows
                  </dd>
                </div>

                <div v-if="experiment.sampling_type === 'range' && experiment.sampling_start_row && experiment.sampling_end_row">
                  <dt class="text-sm font-medium text-neutral-500 mb-2">
                    Row Range
                  </dt>
                  <dd class="text-sm text-neutral-900 font-semibold">
                    {{ experiment.sampling_start_row }} - {{ experiment.sampling_end_row }}
                    <span class="text-neutral-500 font-normal">
                      ({{ experiment.sampling_end_row - experiment.sampling_start_row + 1 }} rows)
                    </span>
                  </dd>
                </div>
              </div>
            </div>

            <div v-else>
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide:filter" class="size-5 text-neutral-400" />
                <span class="text-sm text-neutral-600">Using all dataset rows</span>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Experiment Configuration Summary -->
        <div v-if="latestExecution && latestExecution.agent_executions.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Models Used -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-3">
                <UIcon name="i-lucide-cpu" class="h-6 w-6 text-blue-600" />
                <h2 class="text-xl font-semibold text-neutral-900">
                  Models Used
                </h2>
                <UBadge :label="`${uniqueModels.length}`" color="primary" variant="soft" />
              </div>
            </template>

            <div class="space-y-3">
              <div
                v-for="model in uniqueModels"
                :key="`${model.provider}-${model.name}`"
                class="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200"
              >
                <div>
                  <div class="font-medium text-blue-900">
                    {{ model.name }}
                  </div>
                  <div class="text-sm text-blue-700">
                    {{ model.provider }}
                  </div>
                </div>
                <UBadge :label="`${model.count} agent${model.count > 1 ? 's' : ''}`" color="primary" variant="subtle" />
              </div>
            </div>
          </UCard>

          <!-- Prompts Used -->
          <UCard>
            <template #header>
              <div class="flex items-center gap-3">
                <UIcon name="i-lucide-message-square-text" class="h-6 w-6 text-green-600" />
                <h2 class="text-xl font-semibold text-neutral-900">
                  Prompts Used
                </h2>
                <UBadge :label="`${uniquePrompts.length}`" color="success" variant="soft" />
              </div>
            </template>

            <div class="space-y-3">
              <div
                v-for="prompt in uniquePrompts"
                :key="`${prompt.name}-${prompt.version}`"
                class="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200"
              >
                <div>
                  <div class="font-medium text-green-900">
                    {{ prompt.name }}
                  </div>
                  <div class="text-sm text-green-700">
                    Version: {{ prompt.version }}
                  </div>
                </div>
                <UBadge :label="`${prompt.count} agent${prompt.count > 1 ? 's' : ''}`" color="success" variant="subtle" />
              </div>
            </div>
          </UCard>
        </div>

        <!-- Agent Configurations -->
        <UCard v-if="latestExecution && latestExecution.agent_executions.length > 0">
          <template #header>
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <UIcon name="i-lucide-users" class="h-6 w-6" />
                <h2 class="text-xl font-semibold text-neutral-900">
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
              <div class="space-y-6 pb-4 px-1">
                <!-- Agent Basic Info -->
                <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  <div>
                    <dt class="text-sm font-medium text-neutral-500 mb-1">
                      Agent Name
                    </dt>
                    <dd class="text-sm text-neutral-900 font-medium">
                      {{ agentConfig.agent_name_snapshot }}
                    </dd>
                  </div>
                  <div v-if="agentConfig.agent_team_name_snapshot">
                    <dt class="text-sm font-medium text-neutral-500 mb-1">
                      Team
                    </dt>
                    <dd class="text-sm text-neutral-900">
                      {{ agentConfig.agent_team_name_snapshot }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-neutral-500 mb-1">
                      Execution Order
                    </dt>
                    <dd class="text-sm text-neutral-900">
                      {{ agentConfig.execution_order }}
                    </dd>
                  </div>
                  <div>
                    <dt class="text-sm font-medium text-neutral-500 mb-1">
                      Agent ID
                    </dt>
                    <dd class="text-sm text-neutral-600 font-mono">
                      {{ agentConfig.agent_id }}
                    </dd>
                  </div>
                </div>

                <!-- Model Configuration -->
                <UCard class="bg-blue-50 border-blue-200">
                  <template #header>
                    <div class="flex items-center gap-2">
                      <UIcon name="i-lucide-cpu" class="h-5 w-5 text-blue-600" />
                      <h4 class="text-lg font-medium text-blue-900">
                        Model Configuration
                      </h4>
                    </div>
                  </template>

                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div>
                      <dt class="text-sm font-medium text-blue-700 mb-1">
                        Model Name
                      </dt>
                      <dd class="text-sm text-blue-900 font-medium">
                        {{ agentConfig.model_name_snapshot }}
                      </dd>
                    </div>
                    <div>
                      <dt class="text-sm font-medium text-blue-700 mb-1">
                        Provider
                      </dt>
                      <dd class="text-sm text-blue-900">
                        {{ agentConfig.model_provider_snapshot }}
                      </dd>
                    </div>
                    <div v-if="agentConfig.final_temperature !== null && agentConfig.final_temperature !== undefined">
                      <dt class="text-sm font-medium text-blue-700 mb-1">
                        Temperature
                      </dt>
                      <dd class="text-sm text-blue-900 font-mono">
                        {{ agentConfig.final_temperature }}
                      </dd>
                    </div>
                    <div v-if="agentConfig.final_max_tokens">
                      <dt class="text-sm font-medium text-blue-700 mb-1">
                        Max Tokens
                      </dt>
                      <dd class="text-sm text-blue-900 font-mono">
                        {{ agentConfig.final_max_tokens }}
                      </dd>
                    </div>
                  </div>
                </UCard>

                <!-- Prompt Configuration -->
                <UCard class="bg-green-50 border-green-200">
                  <template #header>
                    <div class="flex items-center gap-2">
                      <UIcon name="i-lucide-message-square-text" class="h-5 w-5 text-green-600" />
                      <h4 class="text-lg font-medium text-green-900">
                        Prompt Configuration
                      </h4>
                    </div>
                  </template>

                  <div class="space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <dt class="text-sm font-medium text-green-700 mb-1">
                          Prompt Name
                        </dt>
                        <dd class="text-sm text-green-900 font-medium">
                          {{ agentConfig.prompt_name_snapshot }}
                        </dd>
                      </div>
                      <div>
                        <dt class="text-sm font-medium text-green-700 mb-1">
                          Version
                        </dt>
                        <dd class="text-sm text-green-900 font-mono">
                          {{ agentConfig.prompt_version_snapshot }}
                        </dd>
                      </div>
                    </div>

                    <!-- System Prompt -->
                    <PromptContentDisplay
                      v-if="agentConfig.final_system_prompt"
                      label="System Prompt"
                      :content="agentConfig.final_system_prompt"
                      type="code"
                    />

                    <!-- User Prompt -->
                    <PromptContentDisplay
                      v-if="agentConfig.final_user_prompt"
                      label="User Prompt"
                      :content="agentConfig.final_user_prompt"
                      type="code"
                    />

                    <!-- Variables -->
                    <PromptVariablesDisplay
                      v-if="agentConfig.final_variables"
                      :variables="agentConfig.final_variables"
                    />
                  </div>
                </UCard>

                <!-- Execution Metadata -->
                <div class="border-t pt-4">
                  <dt class="text-sm font-medium text-neutral-500 mb-2">
                    Execution Metadata
                  </dt>
                  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-xs text-neutral-600">
                    <div>
                      <span class="font-medium">Snapshot ID:</span> {{ agentConfig.id }}
                    </div>
                    <div>
                      <span class="font-medium">Execution ID:</span> {{ agentConfig.execution_id }}
                    </div>
                    <div>
                      <span class="font-medium">Created:</span> {{ new Date(agentConfig.created_at).toLocaleString() }}
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </UAccordion>
        </UCard>

        <!-- No Configuration Available -->
        <UCard v-else>
          <div class="text-center py-12">
            <UIcon name="i-lucide-settings" class="mx-auto h-16 w-16 text-neutral-400 mb-4" />
            <h3 class="text-lg font-medium text-neutral-900 mb-2">
              No Configuration Available
            </h3>
            <p class="text-neutral-600">
              No execution configuration found for this experiment.
            </p>
          </div>
        </UCard>

        <!-- All Executions -->
        <UCard v-if="executions.length > 1">
          <template #header>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-history" class="h-6 w-6" />
              <h2 class="text-xl font-semibold text-neutral-900">
                Execution History
              </h2>
              <UBadge :label="`${executions.length} executions`" color="info" variant="soft" />
            </div>
          </template>

          <div class="space-y-3">
            <div
              v-for="execution in executions.slice().sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())"
              :key="execution.id"
              class="flex items-center justify-between p-4 rounded-lg border"
              :class="{
                'bg-blue-50 border-blue-200': execution.id === latestExecution?.id,
                'bg-neutral-50 border-neutral-200': execution.id !== latestExecution?.id,
              }"
            >
              <div class="flex items-center gap-4">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-medium text-neutral-900">
                      Execution #{{ execution.id }}
                    </span>
                    <UBadge
                      v-if="execution.id === latestExecution?.id"
                      label="Latest"
                      color="primary"
                      variant="subtle"
                      size="xs"
                    />
                  </div>
                  <div class="text-sm text-neutral-600">
                    Started: {{ new Date(execution.started_at).toLocaleString() }}
                  </div>
                  <div v-if="execution.completed_at" class="text-sm text-neutral-600">
                    Completed: {{ new Date(execution.completed_at).toLocaleString() }}
                  </div>
                </div>
              </div>
              <div class="flex items-center gap-3">
                <UBadge
                  :label="execution.status"
                  :color="execution.status === 'completed' ? 'success' : execution.status === 'failed' ? 'error' : 'warning'"
                  variant="subtle"
                  class="capitalize"
                />
                <div v-if="execution.total_tokens" class="text-sm text-neutral-600">
                  {{ execution.total_tokens.toLocaleString() }} tokens
                </div>
                <div v-if="execution.total_cost_usd" class="text-sm text-neutral-600">
                  ${{ execution.total_cost_usd.toFixed(4) }}
                </div>
                <div class="text-sm text-neutral-600">
                  {{ execution.agent_executions?.length || 0 }} agents
                </div>
                <UButton
                  v-if="execution.results_file_path"
                  variant="ghost"
                  color="neutral"
                  icon="i-lucide-download"
                  size="xs"
                  @click="downloadResultsFile(execution.id)"
                >
                  Download
                </UButton>
              </div>
            </div>
          </div>
        </UCard>

        <!-- Experiment Description -->
        <UCard v-if="experiment.description">
          <template #header>
            <div class="flex items-center gap-3">
              <UIcon name="i-lucide-file-text" class="h-6 w-6" />
              <h2 class="text-xl font-semibold text-neutral-900">
                Description
              </h2>
            </div>
          </template>

          <div class="prose prose-sm max-w-none">
            <p class="text-neutral-700 whitespace-pre-wrap">
              {{ experiment.description }}
            </p>
          </div>
        </UCard>
      </div>

      <!-- Error State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          Experiment Not Found
        </h3>
        <p class="text-neutral-500 mb-4">
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
        <p class="text-neutral-600">
          Are you sure you want to delete "{{ experiment?.name }}"? This action cannot be undone.
        </p>
      </template>

      <template #footer>
        <div class="flex gap-3 w-full justify-end">
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
