<script setup lang="ts">
import type { Experiment, ExperimentExecution } from '~/types'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { fetchExperiment, deleteExperiment, rerunExperiment } = useExperiments()
const { fetchExperimentExecutions } = useExperimentExecutions()
const { formatDuration, formatDate } = useUIHelpers()
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

useBreadcrumbLabel(() => experiment.value?.name)

// Set page title and meta
useSeoMeta({
  title: pageTitle,
  description: computed(() =>
    experiment.value
      ? `View details and configuration for experiment: ${experiment.value.name}`
      : 'Loading experiment...',
  ),
})

// How the dataset rows were picked, so "3 rows" reads as a deliberate sample
const samplingLabel = computed(() => {
  const exp = experiment.value
  if (!exp)
    return ''
  if (exp.sampling_type === 'random')
    return `Random sample of ${exp.sampling_size ?? '?'}`
  if (exp.sampling_type === 'range')
    return `Rows ${exp.sampling_start_row ?? '?'}–${exp.sampling_end_row ?? '?'}`
  return 'All dataset rows'
})

// Latest execution for configuration display
const latestExecution = computed(() => {
  if (!executions.value || executions.value.length === 0)
    return null
  return [...executions.value].sort((a, b) =>
    new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  )[0]
})

// Latest execution that produced results, for the Analyze shortcut
const latestCompletedExecution = computed(() => {
  return [...executions.value]
    .filter(e => e.status === 'completed' && e.results_file_path)
    .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0] ?? null
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
    const startTime = parseApiDate(execution.started_at).getTime() / 1000
    const endTime = parseApiDate(execution.completed_at!).getTime() / 1000
    return endTime - startTime
  })

  // Calculate average duration
  const averageDuration = durations.reduce((sum, duration) => sum + duration, 0) / durations.length

  return formatDuration(averageDuration)
})

// Newest first, with what each run took
const executionRows = computed(() => [...executions.value]
  .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
  .map(execution => ({
    execution,
    startedLabel: parseApiDate(execution.started_at).toLocaleString(),
    durationLabel: execution.completed_at
      ? formatDuration((parseApiDate(execution.completed_at).getTime() - parseApiDate(execution.started_at).getTime()) / 1000)
      : null,
  })))

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
  <div class="pb-6">
    <!-- Loading State -->
    <BaseLoadingState v-if="loading" />

    <!-- Experiment Details -->
    <div v-else-if="experiment" class="mx-auto flex max-w-5xl flex-col gap-8">
      <!-- Actions live in the top bar; Back is the breadcrumb -->
      <AppPageActions>
        <UTooltip text="Run this setup with other models, prompts or temperatures">
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-split"
            size="sm"
            :to="{ path: '/experiments/new', query: { from: experiment.id } }"
          >
            Vary
          </UButton>
        </UTooltip>
        <UTooltip text="Create a new execution with the same configuration">
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-play"
            size="sm"
            :loading="isRerunning"
            :disabled="!experiment || experiment.status === 'running'"
            @click="handleRerunExperiment"
          >
            {{ experiment?.status === 'running' ? 'Running…' : 'Re-run' }}
          </UButton>
        </UTooltip>
        <UTooltip :text="latestCompletedExecution ? 'Compare this execution to a ground-truth column' : 'Available once an execution has completed'">
          <UButton
            color="primary"
            icon="i-lucide-chart-column"
            size="sm"
            :disabled="!latestCompletedExecution"
            :to="latestCompletedExecution ? { path: '/analyses/new', query: { execution: latestCompletedExecution.id, name: experiment.name } } : undefined"
          >
            Analyze
          </UButton>
        </UTooltip>
        <UButton
          variant="outline"
          color="error"
          icon="i-lucide-trash-2"
          size="sm"
          @click="() => { showDeleteDialog = true }"
        >
          Delete
        </UButton>
      </AppPageActions>

      <div>
        <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 class="text-xl font-semibold text-highlighted text-balance">
            {{ experiment.name }}
          </h1>
          <UIStatusBadge v-if="experiment.status" :status="experiment.status" />
        </div>
        <p class="mt-0.5 text-sm text-muted tabular-nums">
          Experiment #{{ experiment.id }} · Created {{ formatDate(experiment.created_at) }}
        </p>
        <p v-if="experiment.batch_id" class="mt-1 text-sm text-muted">
          Part of batch
          <NuxtLink :to="`/batches/${experiment.batch_id}`" class="text-toned underline-offset-2 hover:underline">
            {{ experiment.batch_name }}
          </NuxtLink>
        </p>
        <p v-if="experiment.description" class="mt-2 max-w-prose whitespace-pre-wrap text-sm text-toned text-pretty">
          {{ experiment.description }}
        </p>
      </div>

      <!-- Figures: a plain row that wraps, so any number of them lines up -->
      <dl class="flex flex-wrap gap-x-10 gap-y-4">
        <div>
          <dt class="text-xs text-muted">
            Rows
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            <UIRowCount :rows="latestExecution?.row_count ?? experiment.row_count" />
          </dd>
          <p class="text-xs text-muted">
            {{ samplingLabel }}
          </p>
        </div>
        <div>
          <dt class="text-xs text-muted">
            Agents
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            {{ latestExecution?.agent_executions?.length || 0 }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-muted">
            Executions
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            {{ executions.length }}
          </dd>
        </div>
        <div>
          <dt class="text-xs text-muted">
            Duration
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            {{ duration }}
          </dd>
          <p v-if="executions.filter(e => e.status === 'completed').length > 1" class="text-xs text-muted">
            Average of {{ executions.filter(e => e.status === 'completed').length }}
          </p>
        </div>
        <div v-if="latestExecution?.total_tokens">
          <dt class="text-xs text-muted">
            Tokens
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            {{ latestExecution.total_tokens.toLocaleString() }}
          </dd>
        </div>
        <div v-if="latestExecution?.total_cost_usd !== undefined && latestExecution?.total_cost_usd !== null">
          <dt class="text-xs text-muted">
            Cost
          </dt>
          <dd class="mt-0.5 text-lg font-semibold text-highlighted tabular-nums">
            ${{ latestExecution.total_cost_usd.toFixed(4) }}
          </dd>
        </div>
      </dl>

      <ExperimentsSection
        id="agents"
        title="Agents"
        :description="latestExecution && latestExecution.agent_executions.length > 1 ? 'Run from top to bottom. The last agent\'s output is the result.' : undefined"
      >
        <ExperimentsExecutionAgents
          v-if="latestExecution && latestExecution.agent_executions.length > 0"
          :agents="latestExecution.agent_executions"
        />
        <BaseEmptyState
          v-else
          icon="i-lucide-bot"
          title="No configuration recorded"
          message="This experiment has no execution yet."
        />
      </ExperimentsSection>

      <ExperimentsSection id="dataset" title="Dataset">
        <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2">
          <div>
            <dt class="text-xs text-muted">
              Name
            </dt>
            <dd class="mt-0.5 text-sm text-highlighted">
              {{ datasetInfo?.name || experiment.dataset?.name || 'Unknown' }}
            </dd>
          </div>
          <div>
            <dt class="text-xs text-muted">
              Rows used
            </dt>
            <dd class="mt-0.5 text-sm text-highlighted">
              {{ samplingLabel }}
            </dd>
          </div>
          <div v-if="datasetInfo?.description" class="sm:col-span-2">
            <dt class="text-xs text-muted">
              Description
            </dt>
            <dd class="mt-0.5 text-sm text-toned text-pretty">
              {{ datasetInfo.description }}
            </dd>
          </div>
          <div v-if="datasetInfo?.file_path" class="sm:col-span-2">
            <dt class="text-xs text-muted">
              File
            </dt>
            <dd class="mt-0.5 break-all font-mono text-xs text-toned">
              {{ datasetInfo.file_path }}
            </dd>
          </div>
        </dl>
      </ExperimentsSection>

      <ExperimentsSection v-if="executionRows.length > 0" id="executions" title="Executions">
        <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default">
          <li
            v-for="row in executionRows"
            :key="row.execution.id"
            class="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-3"
          >
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm font-medium text-highlighted tabular-nums">Execution #{{ row.execution.id }}</span>
                <UIStatusBadge :status="row.execution.status" size="xs" />
                <UBadge v-if="row.execution.id === latestExecution?.id && executionRows.length > 1" label="Latest" color="neutral" variant="subtle" size="xs" />
              </div>
              <p class="mt-0.5 text-xs text-muted tabular-nums">
                Started {{ row.startedLabel }}<template v-if="row.durationLabel">
                  · took {{ row.durationLabel }}
                </template>
              </p>
            </div>
            <p v-if="row.execution.total_tokens || row.execution.total_cost_usd" class="text-xs text-muted tabular-nums">
              <template v-if="row.execution.total_tokens">
                {{ row.execution.total_tokens.toLocaleString() }} tokens
              </template>
              <template v-if="row.execution.total_tokens && row.execution.total_cost_usd">
                ·
              </template>
              <template v-if="row.execution.total_cost_usd">
                ${{ row.execution.total_cost_usd.toFixed(4) }}
              </template>
            </p>
            <UButton
              v-if="row.execution.results_file_path"
              variant="ghost"
              color="neutral"
              icon="i-lucide-download"
              size="sm"
              @click="() => { downloadResultsFile(row.execution.id) }"
            >
              Results
            </UButton>
          </li>
        </ul>
      </ExperimentsSection>
    </div>

    <!-- Error State -->
    <div v-else class="text-center py-12">
      <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-error mx-auto mb-4" />
      <h3 class="text-lg font-medium text-highlighted mb-2">
        Experiment Not Found
      </h3>
      <p class="text-muted mb-4">
        The experiment you're looking for doesn't exist.
      </p>
      <UButton to="/" variant="solid" color="primary">
        Return to Dashboard
      </UButton>
    </div>

    <!-- Delete Confirmation Modal -->
    <UModal v-model:open="showDeleteDialog" title="Delete Experiment">
      <template #body>
        <p class="text-toned">
          Are you sure you want to delete "{{ experiment?.name }}"? This action cannot be undone.
        </p>
      </template>

      <template #footer>
        <div class="flex gap-3 w-full justify-end">
          <UButton
            variant="outline"
            color="neutral"
            @click="() => { showDeleteDialog = false }"
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
