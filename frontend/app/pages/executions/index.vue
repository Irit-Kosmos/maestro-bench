<script setup lang="ts">
import type { ExecutionListItem } from '~/types'
import type { FilterEntry, FilterSpec, FilterState } from '~/utils/filters'
import { h } from 'vue'
import { executionBatchFilter, executionExperimentFilter, executionFailuresFilter, executionModelsFilter, isAnalyzable } from '~/utils/executions'
import { byOrder, emptyFilterEntry } from '~/utils/filters'
import { DASHBOARD_DATE_RANGES, datasetFilter, dateFilter, statusFilter } from '~/utils/filterSpecs'

definePageMeta({
  title: 'Executions',
  subtitle: 'Every run of every experiment',
})

useSeoMeta({
  title: 'Executions',
  description: 'Every execution of every experiment, to find what failed and pick what to analyze.',
})

const { data: executions, pending, refresh } = await useMyLazyFetch<ExecutionListItem[]>('/executions')

const route = useRoute()
const { runOf } = useLiveRuns()
useRefreshOnRunStatus(refresh)
const { formatDate, formatRelativeDate } = useUIHelpers()
const { downloadResults } = useResultsDownload()
const toast = useToast()

const startedFilter = dateFilter<ExecutionListItem>(execution => execution.started_at, 'Started')
const failuresFilter = executionFailuresFilter()

// Quick test runs (a handful of rows) crowd the list, so they can be filtered out. The choice is remembered per browser
const rowsEntry = useCookie<FilterEntry>('executions-rows-filter', { default: emptyFilterEntry })

// A link from the dashboard, /executions?failures=1&range=7d, opens the list on what its count was made of
const seeded: FilterState = {}
if (route.query.failures)
  seeded[failuresFilter.key] = { mode: 'include', values: ['failed'] }
const seededRange = DASHBOARD_DATE_RANGES[route.query.range as keyof typeof DASHBOARD_DATE_RANGES]
if (seededRange)
  seeded[startedFilter.key] = { mode: 'include', values: [seededRange] }

const filterState = ref<FilterState>({ rows: rowsEntry.value, ...seeded })

watch(() => filterState.value.rows, (entry) => {
  rowsEntry.value = entry ?? emptyFilterEntry()
})

// The link only seeds the filters: once they change, the address would be claiming something untrue
watch(() => JSON.stringify([filterState.value[failuresFilter.key], filterState.value[startedFilter.key]]), () => {
  if (route.query.failures || route.query.range)
    navigateTo({ path: '/executions' }, { replace: true })
})

const selectedIds = ref<number[]>([])

// What the table shows, in order: the panel moves through it
const table = useTemplateRef<{ rows: ExecutionListItem[] }>('table')
const shown = computed(() => table.value?.rows ?? [])

const openId = ref<number | null>(null)
const panelOpen = ref(false)
const openIndex = computed(() => shown.value.findIndex(execution => execution.id === openId.value))
const openExecution = computed(() => (executions.value ?? []).find(execution => execution.id === openId.value) ?? null)

function openPanel(execution: ExecutionListItem) {
  openId.value = execution.id
  panelOpen.value = true
}

function moveInPanel(delta: number) {
  const next = shown.value[openIndex.value + delta]
  if (next)
    openId.value = next.id
}

// The live state of an execution, once it has been seen going
function liveRun(execution: ExecutionListItem) {
  const run = runOf(execution.experiment_id)
  return run?.execution_id === execution.id ? run : undefined
}

// Analyses only read executions that ended well and kept their results: the others are left out, and said so
async function analyze(rows: readonly ExecutionListItem[]) {
  const ready = rows.filter(isAnalyzable)
  if (!ready.length) {
    toast.add({ title: 'Nothing to analyze', description: 'Only completed executions with results can be analyzed.', color: 'neutral', icon: 'i-ph:info-bold' })
    return
  }
  const left = rows.length - ready.length
  if (left > 0) {
    toast.add({
      title: `${left} of ${rows.length} can’t be analyzed`,
      description: 'Only completed executions with results can be.',
      color: 'neutral',
      icon: 'i-ph:info-bold',
    })
  }
  // Oldest first, as the experiment page sends them
  const ordered = [...ready].sort((a, b) => parseApiDate(a.started_at).getTime() - parseApiDate(b.started_at).getTime())
  const names = new Set(ordered.map(execution => execution.experiment_name))
  await navigateTo({
    path: '/analyses/new',
    query: { executions: ordered.map(execution => execution.id).join(','), ...(names.size === 1 ? { name: ordered[0]!.experiment_name } : {}) },
  })
}

// An execution has no name of its own: it is read as its number, and as the nth run of its experiment
const runs = computed(() => {
  const byExperiment = new Map<number, ExecutionListItem[]>()
  for (const execution of executions.value ?? [])
    byExperiment.set(execution.experiment_id, [...(byExperiment.get(execution.experiment_id) ?? []), execution])
  const found = new Map<number, { nth: number, of: number }>()
  for (const siblings of byExperiment.values()) {
    siblings
      .sort((a, b) => parseApiDate(a.started_at).getTime() - parseApiDate(b.started_at).getTime() || a.id - b.id)
      .forEach((execution, index) => found.set(execution.id, { nth: index + 1, of: siblings.length }))
  }
  return found
})

const figureClass = 'text-sm text-toned tabular-nums'
const columns = [
  {
    key: 'id',
    label: 'Execution',
    formatter: (id: number) => `Execution #${id}`,
    render: (row: ExecutionListItem) => {
      const run = runs.value.get(row.id)
      return h('span', { class: 'flex min-h-9 min-w-0 flex-col justify-center' }, [
        h('span', { class: 'truncate leading-5' }, `Execution #${row.id}`),
        run && run.of > 1 ? h('span', { class: 'truncate text-xs font-normal leading-4 text-muted' }, `Run ${run.nth} of ${run.of}`) : null,
      ])
    },
  },
  {
    key: 'experiment_name',
    width: 208,
    label: 'Experiment',
    // A batch's experiments drop the batch prefix: the Batch column already says it
    formatter: (_: unknown, row: ExecutionListItem) => shortExperimentName(row.experiment_name, row.batch_name),
  },
  { key: 'batch_name', width: 168, label: 'Batch', formatter: (_: unknown, row: ExecutionListItem) => row.batch_name || '' },
  { key: 'status', width: 200, label: 'Status' },
  { key: 'dataset_name', width: 160, label: 'Dataset', formatter: (_: unknown, row: ExecutionListItem) => row.dataset_name || '—' },
  {
    key: 'agents',
    width: 200,
    label: 'Models',
    formatter: (_: unknown, row: ExecutionListItem) => modelsOf(row).join(' '),
  },
  { key: 'row_count', width: 150, label: 'Rows' },
  { key: 'duration_seconds', width: 96, label: 'Duration', class: figureClass, formatter: (seconds: number | null) => formatElapsed(seconds) },
  { key: 'total_tokens', width: 88, label: 'Tokens', class: figureClass },
  { key: 'total_cost_usd', width: 88, label: 'Cost', class: figureClass },
  { key: 'started_at', width: 112, label: 'Started' },
]

// Aggregators have no model
function llmAgentsOf(execution: ExecutionListItem) {
  return execution.agents.filter(agent => agent.model)
}

function modelsOf(execution: ExecutionListItem) {
  return [...new Set(llmAgentsOf(execution).map(agent => agent.model))]
}

const filters = computed<FilterSpec<ExecutionListItem>[]>(() => [
  statusFilter(execution => execution.status),
  failuresFilter,
  datasetFilter(execution => execution.dataset_name),
  executionModelsFilter(),
  executionExperimentFilter(() => executions.value ?? []),
  executionBatchFilter(() => executions.value ?? []),
  {
    key: 'rows',
    label: 'Rows',
    icon: 'i-ph-rows-bold',
    // Unknown until the run has results, which is neither small nor not
    value: execution => execution.row_count == null ? undefined : isSmallSample(execution.row_count) ? 'small' : 'full',
    present: value => ({ label: value === 'small' ? `Under ${SMALL_SAMPLE_ROWS} rows` : `${SMALL_SAMPLE_ROWS} rows or more` }),
    compare: byOrder(['small', 'full']),
  },
  startedFilter,
])

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (execution: ExecutionListItem) => openPanel(execution),
  },
  {
    label: 'Open experiment',
    icon: 'i-ph-flask-bold',
    handler: (execution: ExecutionListItem) => navigateTo({ path: `/experiments/${execution.experiment_id}`, hash: '#executions' }),
  },
  {
    label: 'Download results',
    icon: 'i-ph-download-simple-bold',
    show: (execution: ExecutionListItem) => execution.has_results,
    handler: (execution: ExecutionListItem) => downloadResults(execution.id),
  },
]
</script>

<template>
  <BasePageContent
    fill
    :loading="pending && !executions"
  >
    <div v-if="executions && executions.length > 0" class="flex flex-col flex-1 min-h-0">
      <BaseDataTable
        ref="table"
        v-model:selected="selectedIds"
        v-model:filter-state="filterState"
        fill
        :row-height="57"
        :data="executions"
        :columns="columns"
        :filters="filters"
        :actions="actions"
        :loading="pending"
        :row-open="openPanel"
        :active-key="panelOpen ? openId : null"
        selectable
        item-name="execution"
        searchable
        @refresh="refresh"
      >
        <template #selection-actions="{ rows }">
          <UButton
            variant="ghost"
            color="neutral"
            icon="i-ph-chart-bar-bold"
            size="sm"
            @click="analyze(rows)"
          >
            Analyze
          </UButton>
        </template>

        <!-- Above the row's stretched button, so they open the experiment and the batch instead of the panel -->
        <template #experiment_name-cell="{ row }">
          <NuxtLink
            :to="`/experiments/${row.original.experiment_id}`"
            class="relative z-1 inline-flex max-w-full items-center gap-1 rounded text-sm text-toned outline-none hover:text-highlighted hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
            :title="`Open experiment ${row.original.experiment_name}`"
          >
            <UIcon name="i-ph-flask-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
            <span class="truncate">{{ shortExperimentName(row.original.experiment_name, row.original.batch_name) }}</span>
          </NuxtLink>
        </template>

        <template #batch_name-cell="{ row }">
          <NuxtLink
            v-if="row.original.batch_id"
            :to="`/batches/${row.original.batch_id}`"
            class="relative z-1 inline-flex max-w-full items-center gap-1 rounded text-sm text-toned outline-none hover:text-highlighted hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
            :title="`Open batch ${row.original.batch_name}`"
          >
            <UIcon name="i-ph-arrows-split-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
            <span class="truncate">{{ row.original.batch_name }}</span>
          </NuxtLink>
          <span v-else class="text-dimmed">—</span>
        </template>

        <template #status-cell="{ row }">
          <div class="flex items-center gap-3">
            <UIStatusBadge :status="row.original.status" />
            <UIRunProgress :run="liveRun(row.original)" />
          </div>
        </template>

        <template #agents-cell="{ row }">
          <div class="flex min-w-0 items-center gap-1.5 text-sm text-toned">
            <ModelsLabel
              v-if="llmAgentsOf(row.original).length"
              :name="llmAgentsOf(row.original)[0]!.model"
              :provider="llmAgentsOf(row.original)[0]!.provider"
            />
            <span v-else class="text-dimmed">—</span>
            <span
              v-if="modelsOf(row.original).length > 1"
              class="shrink-0 text-xs text-muted tabular-nums"
              :title="modelsOf(row.original).join(', ')"
            >
              +{{ modelsOf(row.original).length - 1 }}
            </span>
          </div>
        </template>

        <template #row_count-cell="{ row }">
          <UIRowCount :rows="row.original.row_count" tone="quiet" class="text-sm" />
          <span v-if="row.original.rows_failed" class="ms-2 text-xs text-error tabular-nums">{{ row.original.rows_failed }} failed</span>
        </template>

        <template #total_tokens-cell="{ row }">
          <span :title="row.original.total_tokens?.toLocaleString()">{{ formatTokens(row.original.total_tokens) }}</span>
        </template>

        <template #total_cost_usd-cell="{ row }">
          <span :title="row.original.total_cost_usd == null ? undefined : `$${row.original.total_cost_usd.toFixed(4)}`">{{ formatCost(row.original.total_cost_usd) }}</span>
        </template>

        <template #started_at-cell="{ row }">
          <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.started_at)">
            {{ formatRelativeDate(row.original.started_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No executions yet"
      message="Each time an experiment runs, its execution is listed here, whether it ended well or not."
      icon="i-ph-clock-counter-clockwise-bold"
      action-label="New experiment"
      action-to="/experiments/new"
    />

    <ExecutionsPanel
      v-model:open="panelOpen"
      :execution="openExecution"
      :run="openExecution ? liveRun(openExecution) : undefined"
      :index="openIndex"
      :total="shown.length"
      :analyzable="!!openExecution && isAnalyzable(openExecution)"
      @navigate="moveInPanel"
      @analyze="openExecution && analyze([openExecution])"
      @download="openExecution && downloadResults(openExecution.id)"
    />
  </BasePageContent>
</template>
