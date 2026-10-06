<script setup lang="ts">
import type { Batch } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import type { SortSpec } from '~/utils/sorts'
import { datasetFilter, dateFilter, earlierRunsFilter, runsFilter, statusFilter } from '~/utils/filterSpecs'
import { dateSort, figureSort, nameSort, statusSort, textSort } from '~/utils/sortSpecs'

definePageMeta({
  title: 'Batches',
})

useSeoMeta({
  title: 'Batches',
  description: 'Groups of experiments generated from one configuration by varying models, prompts or temperatures.',
})

const { data: batches, pending, error, refresh } = await useMyLazyFetch<Batch[]>('/batches')

const { deleteBatch } = useBatches()
const { canEdit } = useCurrentWorkspace()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { showDeleteSuccess, showDeleteError } = useStandardToast()

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const batchId = ref<number | null>(null)

const figureClass = 'text-sm text-toned tabular-nums'
const columns = [
  { key: 'name', label: 'Batch' },
  { key: 'experiments', label: 'Experiments' },
  { key: 'status', label: 'Status' },
  // Across the experiments; the tokens and cost are those of their latest execution
  { key: 'execution_count', label: 'Executions', class: figureClass, formatter: (count: number) => count ? String(count) : '—' },
  { key: 'total_tokens', label: 'Tokens', class: figureClass, formatter: (tokens: number | null) => formatTokens(tokens) },
  { key: 'total_cost_usd', label: 'Cost', class: figureClass, formatter: (cost: number | null) => formatCost(cost) },
  {
    key: 'dataset_name',
    label: 'Dataset',
    formatter: (_: unknown, row: Batch) => row.dataset_name || '—',
  },
  { key: 'created_at', label: 'Created' },
]

const filters: FilterSpec<Batch>[] = [
  statusFilter(batch => batch.status),
  earlierRunsFilter(batch => batch.earlier_execution_statuses),
  datasetFilter(batch => batch.dataset_name),
  runsFilter(batch => batch.execution_count, batch => batch.experiments.length),
  dateFilter(batch => batch.created_at),
]

// In the order of the columns
const sorts: SortSpec<Batch>[] = [
  nameSort(batch => batch.name, 'Batch'),
  figureSort('experiments', 'Experiments', 'i-ph-flask-bold', batch => batch.experiments.length),
  statusSort(batch => batch.status),
  figureSort('executions', 'Executions', 'i-ph-repeat-bold', batch => batch.execution_count),
  figureSort('tokens', 'Tokens', 'i-ph-coins-bold', batch => batch.total_tokens),
  figureSort('cost', 'Cost', 'i-ph-currency-dollar-bold', batch => batch.total_cost_usd),
  textSort('dataset', 'Dataset', 'i-ph-database-bold', batch => batch.dataset_name),
  dateSort(batch => batch.created_at),
]

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (batch: Batch) => navigateTo(`/batches/${batch.id}`),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
    handler: (batch: Batch) => {
      batchId.value = batch.id
      showDeleteDialog.value = true
    },
  },
]

// What is done, out of how many
function progress(batch: Batch) {
  return `${batch.counts.completed ?? 0} / ${batch.experiments.length}`
}

// Runs are watched from the list as well
useRefreshOnRunStatus(refresh)

async function confirmDelete() {
  if (!batchId.value)
    return
  isDeleting.value = true
  try {
    const result = await deleteBatch(batchId.value)
    if (!result.success)
      throw result.error
    showDeleteSuccess('Batch')
    showDeleteDialog.value = false
    batchId.value = null
    await refresh()
  }
  catch {
    showDeleteError('Batch')
  }
  finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <BasePageContent
    :loading="pending && !batches"
    :error="!batches && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UTooltip text="Start from an experiment, then add a variation" :disabled="!canEdit">
        <UIGuardedButton
          color="neutral"
          variant="soft"
          icon="i-ph-plus-bold"
          size="sm"
          to="/experiments/new"
        >
          New batch
        </UIGuardedButton>
      </UTooltip>
    </template>

    <div v-if="batches && batches.length > 0">
      <BaseDataTable
        :data="[...batches]"
        :columns="columns"
        :filters="filters"
        :sorts="sorts"
        :actions="actions"
        :loading="pending"
        :row-to="(batch: Batch) => `/batches/${batch.id}`"
        :row-hint="(batch: Batch) => `#${batch.id}`"
        item-name="batch"
        item-name-plural="batches"
        searchable
        :selectable="canEdit"
        @refresh="refresh"
      >
        <template #selection-actions="{ rows }">
          <StudiesBulkMenu kind="batch" :ids="rows.map((row: Batch) => row.id)" />
        </template>

        <template #experiments-cell="{ row }">
          <span class="text-sm text-toned tabular-nums">{{ progress(row.original) }} done</span>
        </template>

        <template #status-cell="{ row }">
          <div class="flex items-center gap-3">
            <UIStatusBadge :status="row.original.status" />
            <UIStatusHistory :earlier="row.original.earlier_execution_statuses" />
          </div>
        </template>

        <template #created_at-cell="{ row }">
          <span class="text-sm text-muted" :title="formatDate(row.original.created_at)">
            {{ formatRelativeDate(row.original.created_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No batches yet"
      message="A batch runs the same setup with several models, prompt versions or temperatures at once. Open an experiment and choose “Vary…”, or add a variation when you create one."
      icon="i-ph-arrows-split-bold"
      action-label="New experiment"
      action-to="/experiments/new"
      action-requires="editor"
    />

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete batch?"
      message="Only the grouping is removed. Its experiments, executions and results are kept as ordinary experiments."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="confirmDelete"
    />
  </BasePageContent>
</template>
