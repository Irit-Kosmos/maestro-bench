<script setup lang="ts">
import type { Experiment } from '~/types'
import type { FilterEntry, FilterSpec, FilterState } from '~/utils/filters'
import { h, resolveComponent } from 'vue'
import { byOrder, emptyFilterEntry } from '~/utils/filters'
import { datasetFilter, dateFilter, earlierRunsFilter, failuresFilter, runsFilter, statusFilter } from '~/utils/filterSpecs'

// Page meta
definePageMeta({
  title: 'Experiments',
  subtitle: 'Manage and monitor your experiments',
})

// Fetch data directly in the page
const { data: experiments, pending, refresh } = await useMyLazyFetch<Experiment[]>('/experiments')

const route = useRoute()

// Quick test runs (a handful of rows) crowd the list, so they can be filtered out. The choice is remembered per browser
const rowsEntry = useCookie<FilterEntry>('experiments-rows-filter', { default: emptyFilterEntry })

// A link such as /experiments?batch=<id> opens the list on one batch
const batchFromLink = Number(route.query.batch) || undefined
const filterState = ref<FilterState>({
  rows: rowsEntry.value,
  batch: batchFromLink ? { mode: 'include', values: [batchFromLink] } : emptyFilterEntry(),
})

watch(() => filterState.value.rows, (entry) => {
  rowsEntry.value = entry ?? emptyFilterEntry()
})

// The link only seeds the filter: once it changes, the address would be claiming something untrue
watch(() => filterState.value.batch, () => {
  if (route.query.batch)
    navigateTo({ path: '/experiments' }, { replace: true })
})

// Composables
const { deleteExperiment, cancelExperiment } = useExperiments()
const { runOf } = useLiveRuns()
useRefreshOnRunStatus(refresh)
const { formatDate, formatRelativeDate } = useUIHelpers()
const showDeleteDialog = ref(false)
const isDeleting = ref(false)
// Experiments waiting for the delete confirmation: one from a row menu, several from the selection
const pendingDeleteIds = ref<number[]>([])
const selectedIds = ref<number[]>([])

// Page meta
useSeoMeta({
  title: 'Experiments',
  description: 'Manage and monitor your AI agent experiments. Create, view, and analyze experiment results.',
})

// Table configuration
const ExperimentsName = resolveComponent('ExperimentsName')
const figureClass = 'text-sm text-toned tabular-nums'
const columns = [
  {
    key: 'name',
    label: 'Experiment',
    // Capped so a long name truncates instead of pushing the status out of view
    class: 'max-w-72',
    // A batch's experiments drop the batch prefix: the Batch column already says it
    formatter: (_: any, row: Experiment) => shortExperimentName(row.name, row.batch_name),
    render: (row: Experiment, hint?: string) => h(ExperimentsName, { name: row.name, batchName: row.batch_name, hint, stacked: true }),
  },
  {
    key: 'dataset',
    label: 'Dataset',
    formatter: (_: any, row: Experiment) => row.dataset?.name || 'Unknown',
  },
  {
    key: 'batch_name',
    label: 'Batch',
    formatter: (_: any, row: Experiment) => row.batch_name || '',
  },
  {
    key: 'row_count',
    label: 'Rows',
  },
  // The figures of the latest execution; the earlier ones are only counted
  {
    key: 'execution_count',
    label: 'Runs',
    class: figureClass,
    formatter: (count: number | undefined) => count ? String(count) : '—',
  },
  {
    key: 'total_tokens',
    label: 'Tokens',
    class: figureClass,
  },
  {
    key: 'total_cost_usd',
    label: 'Cost',
    class: figureClass,
  },
  {
    key: 'duration_seconds',
    label: 'Duration',
    class: figureClass,
    formatter: (seconds: number | null | undefined) => formatElapsed(seconds),
  },
  {
    key: 'status',
    label: 'Status',
  },
  {
    key: 'created_at',
    label: 'Created',
  },
]

// Batches are told apart by id, but read by the name their experiments carry
const batchNames = computed(() => new Map((experiments.value ?? []).flatMap(exp =>
  exp.batch_id ? [[exp.batch_id, exp.batch_name || `Batch #${exp.batch_id}`] as const] : [],
)))

const filters = computed<FilterSpec<Experiment>[]>(() => [
  statusFilter(exp => exp.status ?? 'pending'),
  earlierRunsFilter(exp => exp.execution_statuses?.slice(1)),
  datasetFilter(exp => exp.dataset?.name),
  {
    key: 'batch',
    label: 'Batch',
    icon: 'i-lucide-split',
    plural: 'batches',
    searchPlaceholder: 'Search a batch…',
    value: exp => exp.batch_id,
    present: id => ({ label: batchNames.value.get(Number(id)) ?? `Batch #${id}`, icon: 'i-lucide-split' }),
  },
  {
    key: 'rows',
    label: 'Rows',
    icon: 'i-lucide-rows-3',
    // Unknown until the run has results, which is neither small nor not
    value: exp => exp.row_count == null ? undefined : isSmallSample(exp.row_count) ? 'small' : 'full',
    present: value => ({ label: value === 'small' ? `Under ${SMALL_SAMPLE_ROWS} rows` : `${SMALL_SAMPLE_ROWS} rows or more` }),
    compare: byOrder(['small', 'full']),
  },
  runsFilter(exp => exp.execution_count),
  failuresFilter(exp => exp.rows_failed),
  dateFilter(exp => exp.created_at),
])

const actions = [
  {
    label: 'Open',
    icon: 'i-lucide-arrow-up-right',
    handler: (experiment: Experiment) => handleViewExperiment(experiment.id),
  },
  {
    label: 'Cancel run',
    icon: 'i-lucide-square',
    show: (experiment: Experiment) => (runOf(experiment.id)?.status ?? experiment.status) === 'running',
    handler: (experiment: Experiment) => handleCancelExperiment(experiment.id),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (experiment: Experiment) => handleDeleteExperiments([experiment.id]),
  },
]

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleCancelExperiment(id: number) {
  const toast = useToast()
  const result = await cancelExperiment(id)
  if (!result.success) {
    toast.add({ title: 'Error', description: 'Failed to cancel the experiment', color: 'error', icon: 'i-lucide:alert-circle' })
    return
  }
  if (result.data.cancelled)
    toast.add({ title: 'Run cancelled', color: 'success', icon: 'i-lucide:check-circle' })
  else
    toast.add({ title: 'Nothing to cancel', description: 'This experiment is no longer running.', color: 'neutral', icon: 'i-lucide:info' })
  await refresh()
}

function handleDeleteExperiments(ids: number[]) {
  pendingDeleteIds.value = ids
  showDeleteDialog.value = true
}

const deleteCount = computed(() => pendingDeleteIds.value.length)

async function confirmDelete() {
  if (!deleteCount.value)
    return

  isDeleting.value = true
  const toast = useToast()

  // One by one: they share a SQLite database, and a failure shouldn't stop the others
  const failed: number[] = []
  for (const id of pendingDeleteIds.value) {
    const { success } = await deleteExperiment(id)
    if (!success)
      failed.push(id)
  }
  const deleted = deleteCount.value - failed.length

  if (deleted > 0) {
    toast.add({
      title: 'Success',
      description: deleted === 1 ? 'Experiment deleted successfully' : `${deleted} experiments deleted successfully`,
      color: 'success',
    })
  }
  if (failed.length > 0) {
    toast.add({
      title: 'Error',
      description: failed.length === 1 ? 'Failed to delete experiment' : `Failed to delete ${failed.length} experiments`,
      color: 'error',
    })
  }

  // Failed ones stay selected so the user can retry them
  selectedIds.value = selectedIds.value.filter(id => failed.includes(id))
  showDeleteDialog.value = false
  pendingDeleteIds.value = []
  isDeleting.value = false

  await refresh()
}

async function handleCreateExperiment() {
  await navigateTo('/experiments/new')
}
</script>

<template>
  <BasePageContent
    fill
    :loading="pending && !experiments"
  >
    <template #before-content>
      <UTooltip text="New experiment" :kbds="['C']">
        <UButton
          color="neutral"
          variant="soft"
          icon="i-lucide-plus"
          size="sm"
          @click="handleCreateExperiment"
        >
          New experiment
        </UButton>
      </UTooltip>
    </template>

    <!-- Experiments Table -->
    <div v-if="experiments && experiments.length > 0" class="flex flex-col flex-1 min-h-0">
      <BaseDataTable
        v-model:selected="selectedIds"
        v-model:filter-state="filterState"
        fill
        :data="experiments"
        :columns="columns"
        :filters="filters"
        :actions="actions"
        :loading="pending"
        :row-to="(exp: Experiment) => `/experiments/${exp.id}`"
        :row-hint="(exp: Experiment) => `#${exp.id}`"
        selectable
        item-name="experiment"
        searchable
        @refresh="refresh"
      >
        <template #selection-actions>
          <UButton
            variant="ghost"
            color="error"
            icon="i-lucide-trash-2"
            size="sm"
            @click="handleDeleteExperiments(selectedIds)"
          >
            Delete
          </UButton>
        </template>

        <!-- Custom cell for status -->
        <template #status-cell="{ row }">
          <div class="flex items-center gap-3">
            <UIStatusBadge :status="row.original.status" />
            <UIStatusHistory :earlier="row.original.execution_statuses?.slice(1)" />
            <UIRunProgress :run="runOf(row.original.id)" />
          </div>
        </template>

        <template #batch_name-cell="{ row }">
          <!-- Above the row's stretched link, so it opens the batch instead of the experiment -->
          <NuxtLink
            v-if="row.original.batch_id"
            :to="`/batches/${row.original.batch_id}`"
            class="relative z-1 inline-flex max-w-48 items-center gap-1 rounded text-sm text-toned outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-primary"
            :title="`Open batch ${row.original.batch_name}`"
          >
            <UIcon name="i-lucide-split" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
            <span class="truncate">{{ row.original.batch_name }}</span>
          </NuxtLink>
          <span v-else class="text-dimmed">—</span>
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

        <!-- Custom cell for created_at -->
        <template #created_at-cell="{ row }">
          <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.created_at)">
            {{ formatRelativeDate(row.original.created_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No experiments yet"
      message="An experiment runs an agent team over a dataset, so you can compare outputs and analyze them."
      icon="i-lucide-flask-conical"
      action-label="New experiment"
      action-to="/experiments/new"
      @action="handleCreateExperiment"
    />

    <UModal v-model:open="showDeleteDialog" :title="deleteCount > 1 ? `Delete ${deleteCount} experiments?` : 'Delete experiment?'">
      <template #body>
        <p class="text-sm text-toned">
          {{ deleteCount > 1 ? 'This deletes these experiments and all of their executions.' : 'This deletes the experiment and all of its executions.' }}
          This can’t be undone.
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
            @click="confirmDelete"
          >
            {{ deleteCount > 1 ? `Delete ${deleteCount} experiments` : 'Delete experiment' }}
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
