<script setup lang="ts">
import type { Experiment, ExperimentExecution } from '~/types'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { fetchExperiment, deleteExperiment, rerunExperiment, cancelExperiment } = useExperiments()
const { fetchExperimentExecutions } = useExperimentExecutions()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { downloadResults: downloadResultsFile } = useResultsDownload()
const { runOf, onStatus } = useLiveRuns()

// State
const experiment = ref<Experiment | null>(null)
const executions = ref<ExperimentExecution[]>([])
const loading = ref(true)
const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const isRerunning = ref(false)
const isCancelling = ref(false)

// Computed
const liveRun = computed(() => runOf(experimentId.value))
const status = computed(() => liveRun.value?.status ?? experiment.value?.status)

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

// How the dataset rows were picked, next to how many there were
const samplingHint = computed(() => {
  const exp = experiment.value
  if (!exp)
    return ''
  if (exp.sampling_type === 'random')
    return 'random sample'
  if (exp.sampling_type === 'range')
    return `rows ${exp.sampling_start_row ?? '?'}–${exp.sampling_end_row ?? '?'}`
  return 'full dataset'
})

// Latest execution for configuration display
const latestExecution = computed(() => {
  if (!executions.value || executions.value.length === 0)
    return null
  return [...executions.value].sort((a, b) =>
    new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
  )[0]
})

// Executions that produced results, oldest first, for the Analyze shortcut
const analyzableExecutions = computed(() => [...executions.value]
  .filter(e => e.status === 'completed' && e.results_file_path)
  .sort((a, b) => new Date(a.started_at).getTime() - new Date(b.started_at).getTime()))

const analyzeLink = computed(() => analyzableExecutions.value.length > 0 && experiment.value
  ? { path: '/analyses/new', query: { executions: analyzableExecutions.value.map(e => e.id).join(','), name: experiment.value.name } }
  : undefined)

// The agents as the ordered list they were set up in, or wired as a graph. Only a sequence has a graph to show.
const agentsView = ref<'list' | 'graph'>('list')
const canShowGraph = computed(() => (latestExecution.value?.agent_executions.length ?? 0) > 1)
const agentsViewOptions = [
  { value: 'list', label: 'List', icon: 'i-ph-list-numbers-bold' },
  { value: 'graph', label: 'Graph', icon: 'i-ph-git-branch-bold' },
]

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
// A silent load keeps the page in place: it is how a run's start and end are picked up
async function loadExperiment({ silent = false } = {}) {
  loading.value = !silent
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
        icon: 'i-ph:warning-circle-bold',
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
      icon: 'i-ph:warning-circle-bold',
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
        icon: 'i-ph:check-circle-bold',
      })
      await navigateTo('/experiments')
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to delete experiment',
        color: 'error',
        icon: 'i-ph:warning-circle-bold',
      })
    }
  }
  catch (error) {
    console.error('Error deleting experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to delete experiment',
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
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
        icon: 'i-ph:play-bold',
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
        icon: 'i-ph:warning-circle-bold',
      })
    }
  }
  catch (error) {
    console.error('Error re-running experiment:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to start experiment re-run',
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
    })
  }
  finally {
    isRerunning.value = false
  }
}

async function handleCancelExperiment() {
  if (!experiment.value)
    return

  isCancelling.value = true
  const result = await cancelExperiment(experiment.value.id)
  isCancelling.value = false

  if (!result.success) {
    toast.add({ title: 'Error', description: 'Failed to cancel the experiment', color: 'error', icon: 'i-ph:warning-circle-bold' })
    return
  }
  if (result.data.cancelled)
    toast.add({ title: 'Run cancelled', color: 'success', icon: 'i-ph:check-circle-bold' })
  else
    toast.add({ title: 'Nothing to cancel', description: 'This experiment is no longer running.', color: 'neutral', icon: 'i-ph:info-bold' })
  await loadExperiment()
}

const datasetName = computed(() => datasetInfo.value?.name || experiment.value?.dataset?.name || 'Unknown')

// Rows the run processed; before any run, what the sampling asks for
const datasetRows = computed(() => {
  const exp = experiment.value
  return latestExecution.value?.row_count
    ?? exp?.row_count
    ?? (exp?.sampling_type === 'random' ? exp.sampling_size : null)
    ?? null
})

// Newest first; what each run took, used and cost sits with the run, not in the page header
const executionRows = computed(() => [...executions.value]
  .sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())
  .map((execution) => {
    const seconds = execution.completed_at
      ? (parseApiDate(execution.completed_at).getTime() - parseApiDate(execution.started_at).getTime()) / 1000
      : null
    return {
      execution,
      duration: seconds === null ? null : formatElapsed(seconds),
      tokens: execution.total_tokens ? formatTokens(execution.total_tokens) : null,
      cost: execution.total_cost_usd ? formatCost(execution.total_cost_usd) : null,
    }
  }))

// A new execution appears when a run starts, its figures when it ends
onStatus((run) => {
  if (!run || run.experiment_id === experimentId.value)
    loadExperiment({ silent: true })
})

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
    <div v-else-if="experiment" class="@container flex max-w-[96rem] flex-col gap-6">
      <!-- Actions live in the top bar; Back is the breadcrumb -->
      <AppPageActions>
        <UTooltip text="Run this setup with other models, prompts or temperatures">
          <UButton
            variant="soft"
            color="neutral"
            icon="i-ph-arrows-split-bold"
            size="sm"
            :to="{ path: '/experiments/new', query: { from: experiment.id } }"
          >
            Vary
          </UButton>
        </UTooltip>
        <UTooltip v-if="status === 'running'" text="Stop the run in progress">
          <UButton
            variant="soft"
            color="error"
            icon="i-ph-square-bold"
            size="sm"
            :loading="isCancelling"
            @click="handleCancelExperiment"
          >
            Cancel run
          </UButton>
        </UTooltip>
        <UTooltip v-else text="Create a new execution with the same configuration">
          <UButton
            variant="soft"
            color="neutral"
            icon="i-ph-play-bold"
            size="sm"
            :loading="isRerunning"
            :disabled="!experiment"
            @click="handleRerunExperiment"
          >
            Re-run
          </UButton>
        </UTooltip>
        <UTooltip :text="analyzeLink ? (analyzableExecutions.length > 1 ? 'Compare all executions to a ground-truth column' : 'Compare this execution to a ground-truth column') : 'Available once an execution has completed'">
          <UButton
            color="neutral"
            variant="soft"
            icon="i-ph-chart-bar-bold"
            size="sm"
            :disabled="!analyzeLink"
            :to="analyzeLink"
          >
            Analyze
          </UButton>
        </UTooltip>
        <UButton
          variant="soft"
          color="error"
          icon="i-ph-trash-bold"
          size="sm"
          @click="() => { showDeleteDialog = true }"
        >
          Delete
        </UButton>
      </AppPageActions>

      <!-- Identity only: what it is and when. Everything measurable lives with the thing it measures -->
      <header>
        <h1 class="flex items-center gap-2.5 text-xl font-semibold text-highlighted">
          <UIStatusIcon :status="status" size="size-5" tooltip />
          <span class="min-w-0 text-balance">{{ experiment.name }}</span>
        </h1>
        <!-- Each fact has its own icon; the id is the quietest, the batch is the only link -->
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <UIMetaItem icon="i-ph-hash-bold" label="Experiment" class="tabular-nums">
            {{ experiment.id }}
          </UIMetaItem>
          <UIMetaItem icon="i-ph-calendar-blank-bold" label="Created" class="tabular-nums">
            {{ formatDate(experiment.created_at) }}
          </UIMetaItem>
          <UIMetaItem v-if="experiment.batch_id" icon="i-ph-arrows-split-bold" label="Batch">
            <UIMetaLink :to="`/batches/${experiment.batch_id}`">
              {{ experiment.batch_name }}
            </UIMetaLink>
          </UIMetaItem>
        </div>
        <p v-if="experiment.description" class="mt-1.5 max-w-prose whitespace-pre-wrap text-sm text-toned text-pretty">
          {{ experiment.description }}
        </p>
      </header>

      <!-- What is run (agents) takes the wide column; what it runs on and what came out stack beside it -->
      <div class="grid gap-x-10 gap-y-6 @4xl:grid-cols-[minmax(0,1fr)_21rem]">
        <ExperimentsSection
          id="agents"
          title="Agents"
          icon="i-ph-robot-bold"
          :count="latestExecution?.agent_executions.length ?? 0"
          :description="latestExecution && latestExecution.agent_executions.length > 1 ? 'Run from top to bottom. The last agent\'s output is the result.' : undefined"
        >
          <template v-if="canShowGraph" #actions>
            <UTabs
              v-model="agentsView"
              :items="agentsViewOptions"
              :content="false"
              variant="pill"
              color="neutral"
              size="xs"
              :ui="{
                indicator: 'bg-default ring ring-default shadow-xs',
                trigger: 'data-[state=active]:text-highlighted',
              }"
              aria-label="View"
            />
          </template>

          <template v-if="latestExecution && latestExecution.agent_executions.length > 0">
            <ExperimentsExecutionAgentsGraph
              v-if="canShowGraph && agentsView === 'graph'"
              :agents="latestExecution.agent_executions"
            />
            <ExperimentsExecutionAgents
              v-else
              :agents="latestExecution.agent_executions"
            />
          </template>
          <BaseEmptyState
            v-else
            icon="i-ph-robot-bold"
            title="No configuration recorded"
            message="This experiment has no execution yet."
          />
        </ExperimentsSection>

        <div class="flex min-w-0 flex-col gap-5">
          <!-- Values describe themselves, so the icon names the fact (and the title says it on hover) -->
          <ExperimentsSection id="dataset" title="Dataset" icon="i-ph-database-bold" compact>
            <ul class="flex flex-col gap-2 text-sm text-highlighted">
              <li>
                <UIMetaItem icon="i-ph-tag-bold" label="Name">
                  <UIMetaLink v-if="experiment.dataset_id" :to="`/datasets/${experiment.dataset_id}`">
                    {{ datasetName }}
                  </UIMetaLink>
                  <span v-else class="truncate">{{ datasetName }}</span>
                </UIMetaItem>
              </li>
              <li>
                <UIMetaItem icon="i-ph-rows-bold" label="Rows used" class="tabular-nums">
                  <UIRowCount :rows="datasetRows" />
                  <span class="text-muted">· {{ samplingHint }}</span>
                </UIMetaItem>
              </li>
              <li v-if="datasetInfo?.file_path">
                <UIMetaItem icon="i-ph-file-xls-bold" label="File">
                  <span class="truncate font-mono text-xs text-toned" :title="datasetInfo.file_path">{{ datasetInfo.file_path }}</span>
                </UIMetaItem>
              </li>
              <li v-if="datasetInfo?.description" class="ps-5">
                <p class="line-clamp-2 text-xs text-muted text-pretty" :title="datasetInfo.description">
                  {{ datasetInfo.description }}
                </p>
              </li>
            </ul>
          </ExperimentsSection>

          <ExperimentsSection
            v-if="executionRows.length > 0"
            id="executions"
            title="Executions"
            icon="i-ph-clock-counter-clockwise-bold"
            :count="executionRows.length"
            compact
          >
            <ul class="divide-y divide-default overflow-hidden rounded-lg border border-default">
              <li
                v-for="row in executionRows"
                :key="row.execution.id"
                class="flex items-center gap-2 py-2 pl-3 pr-2"
              >
                <div class="min-w-0 flex-1">
                  <div class="flex flex-wrap items-center gap-x-2 gap-y-0.5">
                    <UIStatusBadge :status="row.execution.status" />
                    <span class="text-sm font-medium text-highlighted tabular-nums">#{{ row.execution.id }}</span>
                    <UBadge v-if="row.execution.id === latestExecution?.id && executionRows.length > 1" label="Latest" color="neutral" variant="subtle" size="xs" />
                    <span class="text-xs text-muted tabular-nums" :title="formatDate(row.execution.started_at)">{{ formatRelativeDate(row.execution.started_at) }}</span>
                  </div>
                  <UIRunProgress v-if="liveRun?.execution_id === row.execution.id" :run="liveRun" class="mt-1.5" />
                  <!-- What the run took, used and cost: only what exists (a running one has none yet) -->
                  <div v-if="row.duration || row.tokens || row.cost" class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-toned tabular-nums">
                    <UIMetaItem v-if="row.duration" icon="i-ph-clock-bold" label="Duration">
                      {{ row.duration }}
                    </UIMetaItem>
                    <UIMetaItem v-if="row.tokens" icon="i-ph-text-aa-bold" label="Tokens">
                      <span :title="row.execution.total_tokens?.toLocaleString()">{{ row.tokens }}</span>
                    </UIMetaItem>
                    <UIMetaItem v-if="row.cost" icon="i-ph-coins-bold" label="Cost">
                      <span :title="`$${row.execution.total_cost_usd?.toFixed(4)}`">{{ row.cost }}</span>
                    </UIMetaItem>
                  </div>
                </div>
                <UTooltip v-if="row.execution.results_file_path" text="Download results">
                  <UButton
                    variant="ghost"
                    color="neutral"
                    icon="i-ph-download-simple-bold"
                    size="sm"
                    :aria-label="`Download results of execution #${row.execution.id}`"
                    @click="() => { downloadResultsFile(row.execution.id) }"
                  />
                </UTooltip>
              </li>
            </ul>
          </ExperimentsSection>
        </div>
      </div>
    </div>

    <!-- Error State -->
    <div v-else class="text-center py-12">
      <UIcon name="i-ph:warning-circle-bold" class="w-12 h-12 text-error mx-auto mb-4" />
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
