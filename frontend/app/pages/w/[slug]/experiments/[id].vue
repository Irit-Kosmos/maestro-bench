<script setup lang="ts">
import type { Experiment, ExperimentExecution } from '~/types'
import type { FetchErrorKind } from '~/utils/fetchError'
import { useResizeObserver } from '@vueuse/core'

// Route params
const route = useRoute()
const experimentId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const { ok, info, fail } = useStandardToast()
const { fetchExperiment, deleteExperiment, rerunExperiment, cancelExperiment, resampleExperiment } = useExperiments()
const { fetchExperimentExecutions } = useExperimentExecutions()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { downloadResults: downloadResultsFile } = useResultsDownload()
const { runOf, onStatus } = useLiveRuns()
const { canEdit } = useCurrentWorkspace()

// State
const experiment = ref<Experiment | null>(null)
const executions = ref<ExperimentExecution[]>([])
const loading = ref(true)
// Why the experiment could not be shown, once a load has failed with nothing on screen
const loadError = ref<FetchErrorKind | null>(null)
const showDeleteDialog = ref(false)
const showCancelDialog = ref(false)
const isDeleting = ref(false)
const isRerunning = ref(false)
const isCancelling = ref(false)
const isResampling = ref(false)

// Computed
const liveRun = computed(() => runOf(experimentId.value))
const status = computed(() => liveRun.value?.status ?? experiment.value?.status)

const pageTitle = computed(() => {
  return experiment.value ? experiment.value.name : 'Loading…'
})

useBreadcrumbLabel(() => experiment.value?.name)

// Set page title and meta
useSeoMeta({
  title: pageTitle,
  description: computed(() =>
    experiment.value
      ? `View details and configuration for experiment: ${experiment.value.name}`
      : 'Loading experiment…',
  ),
})

// How the dataset rows were picked, next to how many there were, and whether the
// next run takes the same rows. A random sample is redrawn on each run, except in a
// batch, where every run uses the batch's sample so the variants stay comparable.
const samplingHint = computed(() => {
  const exp = experiment.value
  if (!exp)
    return ''
  if (exp.sampling_type === 'random')
    return exp.batch_id ? 'random sample, shared by the batch' : 'random sample, kept between runs'
  if (exp.sampling_type === 'range')
    return `rows ${exp.sampling_start_row ?? '?'}–${exp.sampling_end_row ?? '?'}, same on every run`
  return 'full dataset, same on every run'
})

// Latest execution for configuration display
const latestExecution = computed(() => {
  if (!executions.value || executions.value.length === 0)
    return null
  return [...executions.value].sort((a, b) =>
    parseApiDate(b.started_at).getTime() - parseApiDate(a.started_at).getTime(),
  )[0]
})

// Executions that produced results, oldest first, for the Analyze shortcut
const analyzableExecutions = computed(() => [...executions.value]
  .filter(e => e.status === 'completed' && e.results_file_path)
  .sort((a, b) => parseApiDate(a.started_at).getTime() - parseApiDate(b.started_at).getTime()))

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
      loadError.value = null
    }
    else {
      // A background refresh that fails leaves what is on screen alone
      if (!experiment.value)
        loadError.value = fetchErrorKind(result.error)
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
    if (!experiment.value)
      loadError.value = 'error'
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
      ok('Experiment deleted')
      await navigateTo('/experiments')
    }
    else {
      fail('Couldn’t delete the experiment')
    }
  }
  catch (error) {
    console.error('Error deleting experiment:', error)
    fail('Couldn’t delete the experiment')
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
      if (result.data.status === 'queued')
        info('Re-run queued', 'Your workspace is running as many experiments as it may: this one will start as soon as a slot is free.')
      else
        ok('Re-run started', { description: 'A new execution was created.' })

      // Refresh the experiment and executions to show the new execution
      await loadExperiment({ silent: true })

      // Show the status right away, before the run says anything
      if (experiment.value) {
        experiment.value.status = result.data.status === 'queued' ? 'queued' : 'running'
      }
    }
    else {
      fail('Couldn’t start the re-run')
    }
  }
  catch (error) {
    console.error('Error re-running experiment:', error)
    fail('Couldn’t start the re-run')
  }
  finally {
    isRerunning.value = false
  }
}

async function handleCancelExperiment() {
  showCancelDialog.value = false
  if (!experiment.value)
    return

  isCancelling.value = true
  const result = await cancelExperiment(experiment.value.id)
  isCancelling.value = false

  if (!result.success) {
    fail('Couldn’t cancel the run')
    return
  }
  if (result.data.cancelled)
    ok('Run cancelled')
  else
    info('Nothing to cancel', 'This experiment is no longer running or waiting.')
  await loadExperiment({ silent: true })
}

// A random sample is kept between runs; once redrawn, the next run takes other rows than the latest one
const canResample = computed(() => canEdit.value && experiment.value?.sampling_type === 'random' && !experiment.value.batch_id)
const sampleRedrawn = computed(() => {
  const seed = experiment.value?.sampling_seed
  const latest = latestExecution.value ? sampleSeed(latestExecution.value) : null
  return seed != null && latest != null && seed !== latest
})

async function handleResample() {
  if (!experiment.value)
    return

  isResampling.value = true
  const result = await resampleExperiment(experiment.value.id)
  isResampling.value = false

  if (!result.success) {
    fail('Couldn’t draw a new sample')
    return
  }
  experiment.value.sampling_seed = result.data.sampling_seed
  ok('New sample drawn', { description: 'The next run takes other rows.' })
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

// Seed of the random sample a run drew: runs with the same seed ran on the same rows
function sampleSeed(execution: { dataset_snapshot: string }): number | null {
  try {
    return JSON.parse(execution.dataset_snapshot).sampling_config?.sampling_seed ?? null
  }
  catch {
    return null
  }
}

// Newest first; what each run took, used and cost sits with the run, not in the page header
const executionRows = computed(() => [...executions.value]
  .sort((a, b) => parseApiDate(b.started_at).getTime() - parseApiDate(a.started_at).getTime())
  .map((execution) => {
    const seconds = execution.completed_at
      ? (parseApiDate(execution.completed_at).getTime() - parseApiDate(execution.started_at).getTime()) / 1000
      : null
    return {
      execution,
      seed: sampleSeed(execution),
      duration: seconds === null ? null : formatElapsed(seconds),
      tokens: execution.total_tokens ? formatTokens(execution.total_tokens) : null,
      cost: execution.total_cost_usd ? formatCost(execution.total_cost_usd) : null,
    }
  }))

// A fade at the foot of the capped list says there is more below; it goes once the end is reached
const executionsList = useTemplateRef<HTMLElement>('executionsList')
const moreBelow = ref(false)
function measureExecutionsList() {
  const el = executionsList.value
  moreBelow.value = !!el && el.scrollHeight - el.scrollTop - el.clientHeight > 4
}
useResizeObserver(executionsList, measureExecutionsList)
watch([executionRows, executionsList], () => nextTick(measureExecutionsList))

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
  experiment.value = null
  loadError.value = null
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
        <UIGuardedButton
          :data-tooltip="canEdit ? 'Run this setup with other models, prompts or temperatures' : undefined"
          variant="soft"
          color="neutral"
          icon="i-ph-arrows-split-bold"
          size="sm"
          :to="{ path: '/experiments/new', query: { from: experiment.id } }"
        >
          Vary
        </UIGuardedButton>
        <UIGuardedButton
          v-if="status === 'running' || status === 'queued'" :data-tooltip="!canEdit ? undefined : status === 'queued' ? 'Take the run out of the queue' : 'Stop the run in progress'"
          variant="soft"
          color="error"
          icon="i-ph-stop-circle-bold"
          size="sm"
          :loading="isCancelling"
          @click="() => { showCancelDialog = true }"
        >
          Cancel run
        </UIGuardedButton>
        <UIGuardedButton
          v-else :data-tooltip="canEdit ? 'Create a new execution with the same configuration' : undefined"
          variant="soft"
          color="neutral"
          icon="i-ph-play-bold"
          size="sm"
          :loading="isRerunning"
          :disabled="!experiment"
          @click="handleRerunExperiment"
        >
          Re-run
        </UIGuardedButton>
        <UIGuardedButton
          :data-tooltip="!canEdit ? undefined : analyzeLink ? (analyzableExecutions.length > 1 ? 'Compare all executions to a ground-truth column' : 'Compare this execution to a ground-truth column') : 'Available once an execution has completed'"
          color="neutral"
          variant="soft"
          icon="i-ph-chart-bar-bold"
          size="sm"
          :disabled="!analyzeLink"
          :to="analyzeLink"
        >
          Analyze
        </UIGuardedButton>
        <UDropdownMenu
          v-if="canEdit"
          :items="[{ label: 'Delete experiment', icon: 'i-ph-trash-bold', color: 'error', onSelect: () => { showDeleteDialog = true } }]"
          :content="{ align: 'end' }"
        >
          <UButton icon="i-ph-dots-three-bold" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
        </UDropdownMenu>
      </AppPageActions>

      <!-- Identity only: what it is and when. Everything measurable lives with the thing it measures -->
      <header>
        <h1 class="flex items-center gap-2.5 text-xl font-semibold text-highlighted">
          <UIStatusIcon :status="status" size="size-5" tooltip />
          <span class="min-w-0 text-balance">{{ experiment.name }}</span>
        </h1>
        <!-- Each fact has its own icon; the id is the quietest, the batch is the only link -->
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <UIMetaItem icon="i-ph-hash-bold" label="Experiment">
            {{ experiment.id }}
          </UIMetaItem>
          <UIMetaItem icon="i-ph-calendar-blank-bold" label="Created">
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
        <StudiesItemStudies :id="experiment.id" kind="experiment" class="mt-2.5" />
      </header>

      <!-- What is run (agents) takes the wide column; what it runs on and what came out stack beside it -->
      <div class="grid gap-x-10 gap-y-6 @4xl:grid-cols-[minmax(0,1fr)_21rem]">
        <ExperimentsSection
          id="agents"
          title="Agents"
          icon="i-ph-ghost-bold"
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
            icon="i-ph-ghost-bold"
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
                <UIMetaItem icon="i-ph-rows-bold" label="Rows used">
                  <UIRowCount :rows="datasetRows" />
                  <span class="text-muted">· {{ samplingHint }}</span>
                </UIMetaItem>
              </li>
              <li v-if="experiment.sampling_type === 'random' && experiment.sampling_seed != null" class="flex items-center justify-between gap-2">
                <UIMetaItem icon="i-ph-dice-five-bold" label="Sample seed">
                  <span class="shrink-0 whitespace-nowrap">seed {{ experiment.sampling_seed }}</span>
                  <span v-if="sampleRedrawn" class="truncate text-muted" title="New rows on the next run">· new rows on the next run</span>
                </UIMetaItem>
                <UButton
                  v-if="canResample"
                  label="Resample"
                  icon="i-ph-shuffle-bold"
                  variant="ghost"
                  color="neutral"
                  size="xs"
                  class="-my-1 shrink-0 whitespace-nowrap"
                  :loading="isResampling"
                  @click="handleResample"
                />
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
            <!-- Capped so a long history doesn't push Notes off screen -->
            <div class="relative">
              <ul
                ref="executionsList"
                class="max-h-80 divide-y divide-default overflow-y-auto overscroll-contain rounded-lg border border-default"
                @scroll.passive="measureExecutionsList"
              >
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
                      <span class="text-xs text-muted" :title="formatDate(row.execution.started_at)">{{ formatRelativeDate(row.execution.started_at) }}</span>
                    </div>
                    <UIRunProgress v-if="liveRun?.execution_id === row.execution.id" :run="liveRun" class="mt-1.5" />
                    <!-- What the run took, used and cost: only what exists (a running one has none yet) -->
                    <div v-if="row.duration || row.tokens || row.cost" class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-toned tabular-nums">
                      <UIMetaItem v-if="row.duration" icon="i-ph-clock-bold" label="Duration">
                        {{ row.duration }}
                      </UIMetaItem>
                      <UIMetaItem v-if="row.tokens" icon="i-ph-text-aa-bold" label="Tokens">
                        <span :title="formatCount(row.execution.total_tokens)">{{ row.tokens }}</span>
                      </UIMetaItem>
                      <UIMetaItem v-if="row.cost" icon="i-ph-coins-bold" label="Cost">
                        <span :title="formatCostPrecise(row.execution.total_cost_usd)">{{ row.cost }}</span>
                      </UIMetaItem>
                    </div>
                    <!-- Runs with the same seed ran on the same rows -->
                    <p v-if="row.seed !== null" class="mt-1 text-xs text-muted tabular-nums">
                      Random sample, seed {{ row.seed }}
                    </p>
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
              <div
                class="pointer-events-none absolute inset-x-px bottom-px h-12 rounded-b-lg bg-gradient-to-t from-(--ui-bg) to-transparent transition-opacity duration-150"
                :class="moreBelow ? 'opacity-100' : 'opacity-0'"
                aria-hidden="true"
              />
            </div>
          </ExperimentsSection>
        </div>
      </div>

      <ExperimentsSection id="notes" title="Notes" icon="i-ph-notepad-bold" description="What you notice and decide about this run. Notes show up in the activity of every study that holds it.">
        <NotesJournal kind="experiment" :item-id="experiment.id" />
      </ExperimentsSection>
    </div>

    <!-- Error State -->
    <BaseErrorState
      v-else
      :kind="loadError ?? 'not-found'"
      action-to="/experiments"
      action-label="Back to experiments"
      @retry="loadExperiment()"
    />

    <!-- Delete Confirmation Modal -->
    <BaseConfirmDialog
      v-model:open="showCancelDialog"
      :title="status === 'queued' ? 'Take this run out of the queue?' : 'Stop this run?'"
      :message="status === 'queued' ? 'It leaves the queue without running. You can re-run it later.' : 'The run stops now. You can re-run the experiment later.'"
      :confirm-label="status === 'queued' ? 'Remove from queue' : 'Stop run'"
      variant="warning"
      :loading="isCancelling"
      @confirm="handleCancelExperiment"
    />

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete experiment?"
      :message="`“${experiment?.name}” and all of its executions are deleted. This can’t be undone.`"
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="handleDeleteExperiment"
    />
  </div>
</template>
