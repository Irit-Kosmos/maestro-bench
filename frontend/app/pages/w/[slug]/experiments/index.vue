<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Experiment } from '~/types'
import type { FilterEntry, FilterSpec, FilterState } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import type { SortSpec } from '~/utils/sorts'
import { useLocalStorage } from '@vueuse/core'
import { h, resolveComponent } from 'vue'
import { useGroupBy } from '~/composables/useGroupBy'
import { useSortBy } from '~/composables/useSortBy'
import { runsSummary } from '~/utils/executions'
import { byOrder, emptyFilterEntry } from '~/utils/filters'
import { DASHBOARD_DATE_RANGES, datasetFilter, dateFilter, earlierRunsFilter, failuresFilter, runsFilter, statusFilter } from '~/utils/filterSpecs'
import { dateSort, figureSort, nameSort, statusSort, textSort } from '~/utils/sortSpecs'

// Page meta
definePageMeta({
  title: 'Experiments',
})

// Fetch data directly in the page
const { data: experiments, pending, error, refresh } = await useMyLazyFetch<Experiment[]>('/experiments')

const route = useRoute()

// Quick test runs (a handful of rows) crowd the list, so they can be filtered out. The choice is remembered per browser
const rowsEntry = useLocalStorage<FilterEntry>(workspaceStorageKey('maestro:experiments-rows-filter'), emptyFilterEntry())

const failures = failuresFilter<Experiment>(exp => exp.execution_count ? { status: exp.execution_statuses?.[0], rows_failed: exp.rows_failed } : undefined)
const lastRunFilter = dateFilter<Experiment>(exp => exp.last_run_at, 'Last run')

// A link such as /experiments?batch=<id> opens the list on one batch, and the dashboard's
// /experiments?failures=1&range=7d on what its count was made of
const batchFromLink = Number(route.query.batch) || undefined
const seeded: FilterState = {}
if (route.query.failures)
  seeded[failures.key] = { mode: 'include', values: ['failed'] }
const rangeFromLink = DASHBOARD_DATE_RANGES[route.query.range as keyof typeof DASHBOARD_DATE_RANGES]
if (rangeFromLink)
  seeded[lastRunFilter.key] = { mode: 'include', values: [rangeFromLink] }
const filterState = ref<FilterState>({
  rows: rowsEntry.value,
  batch: batchFromLink ? { mode: 'include', values: [batchFromLink] } : emptyFilterEntry(),
  ...seeded,
})

watch(() => filterState.value.rows, (entry) => {
  rowsEntry.value = entry ?? emptyFilterEntry()
})

// The link only seeds the filters: once they change, the address would be claiming something untrue
watch(() => JSON.stringify([filterState.value.batch, filterState.value[failures.key], filterState.value[lastRunFilter.key]]), () => {
  if (route.query.batch || route.query.failures || route.query.range)
    navigateTo({ path: '/experiments' }, { replace: true })
})

// Composables
const { deleteExperiment, cancelExperiment } = useExperiments()
const { canEdit } = useCurrentWorkspace()
const { ok, info, fail, showDeleteSuccess, showDeleteError } = useStandardToast()
const { runOf } = useLiveRuns()
useRefreshOnRunStatus(refresh)
const { formatDate, formatRelativeDate } = useUIHelpers()
const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const showCancelDialog = ref(false)
const isCancelling = ref(false)
const pendingCancel = ref<Experiment | null>(null)
// Experiments waiting for the delete confirmation: one from a row menu, several from the selection
const pendingDeleteIds = ref<number[]>([])
const selectedIds = ref<number[]>([])

// Page meta
useSeoMeta({
  title: 'Experiments',
  description: 'Manage and monitor your AI agent experiments. Create, view, and analyze experiment results.',
})

// Table configuration
// How the list is grouped is remembered per browser
const groupBy = useGroupBy('maestro:experiments-group-by', 'batch')
// Remembered per browser too; the list keeps the order the API gives (the latest first) until one is picked
const sortBy = useSortBy('maestro:experiments-sort-by')

const ExperimentsName = resolveComponent('ExperimentsName')
const figureClass = 'text-sm text-toned tabular-nums'
const columns = computed(() => [
  {
    key: 'name',
    label: 'Experiment',
    // The one column without a width: it takes what the others leave, and truncates
    // A batch's experiments drop the batch prefix: the Batch column already says it
    formatter: (_: any, row: Experiment) => shortExperimentName(row.name, row.batch_name),
    render: (row: Experiment, hint?: string) => h(ExperimentsName, { name: row.name, batchName: row.batch_name, hint, stacked: true }),
  },
  {
    key: 'dataset',
    width: 160,
    label: 'Dataset',
    formatter: (_: any, row: Experiment) => row.dataset?.name || 'Unknown',
  },
  {
    key: 'batch_name',
    width: 176,
    label: 'Batch',
    formatter: (_: any, row: Experiment) => row.batch_name || '',
    // The batch section says it, but the search still finds a batch by its name
    hidden: groupBy.value === 'batch',
  },
  {
    key: 'row_count',
    width: 176,
    label: 'Rows',
  },
  // The figures of the latest execution; the earlier ones are only counted
  {
    key: 'execution_count',
    width: 104,
    label: 'Executions',
    class: figureClass,
    formatter: (count: number | undefined) => count ? String(count) : '—',
  },
  {
    key: 'total_tokens',
    width: 80,
    label: 'Tokens',
    class: figureClass,
  },
  {
    key: 'total_cost_usd',
    width: 88,
    label: 'Cost',
    class: figureClass,
  },
  {
    key: 'duration_seconds',
    width: 88,
    label: 'Duration',
    class: figureClass,
    formatter: (seconds: number | null | undefined) => formatElapsed(seconds),
  },
  {
    key: 'status',
    // The icon and the dots of the earlier executions: the progress of a run in flight sits under the row count
    width: 144,
    label: 'Status',
  },
  {
    key: 'created_at',
    width: 112,
    label: 'Created',
  },
])

// Batches are told apart by id, but read by the name their experiments carry
const batchNames = computed(() => new Map((experiments.value ?? []).flatMap(exp =>
  exp.batch_id ? [[exp.batch_id, exp.batch_name || `Batch #${exp.batch_id}`] as const] : [],
)))

// The experiments of a batch sit together under it, the others stay where their date puts them
const groups: GroupSpec<Experiment>[] = [
  {
    key: 'batch',
    label: 'Batch',
    icon: 'i-ph-arrows-split-bold',
    flow: true,
    value: exp => exp.batch_id,
    present: id => ({ label: batchNames.value.get(Number(id)) ?? `Batch #${id}`, icon: 'i-ph-arrows-split-bold' }),
    link: id => `/batches/${id}`,
    summary: items => runsSummary(items.map(exp => ({ status: runOf(exp.id)?.status ?? exp.status, rows_failed: exp.rows_failed }))),
    rail: 'bg-neutral-300 dark:bg-neutral-600',
  },
]

// In the order of the columns. Inside a batch's section the experiments are sorted among themselves
const sorts: SortSpec<Experiment>[] = [
  nameSort(exp => shortExperimentName(exp.name, exp.batch_name), 'Experiment'),
  textSort('dataset', 'Dataset', 'i-ph-database-bold', exp => exp.dataset?.name),
  textSort('batch', 'Batch', 'i-ph-arrows-split-bold', exp => exp.batch_name),
  figureSort('rows', 'Rows', 'i-ph-rows-bold', exp => exp.row_count),
  figureSort('executions', 'Executions', 'i-ph-repeat-bold', exp => exp.execution_count),
  figureSort('tokens', 'Tokens', 'i-ph-coins-bold', exp => exp.total_tokens),
  figureSort('cost', 'Cost', 'i-ph-currency-dollar-bold', exp => exp.total_cost_usd),
  figureSort('duration', 'Duration', 'i-ph-timer-bold', exp => exp.duration_seconds),
  statusSort(exp => exp.status ?? 'pending'),
  dateSort(exp => exp.created_at),
]

const filters = computed<FilterSpec<Experiment>[]>(() => [
  statusFilter(exp => exp.status ?? 'pending'),
  earlierRunsFilter(exp => exp.execution_statuses?.slice(1)),
  datasetFilter(exp => exp.dataset?.name),
  {
    key: 'batch',
    label: 'Batch',
    icon: 'i-ph-arrows-split-bold',
    plural: 'batches',
    searchPlaceholder: 'Search a batch…',
    value: exp => exp.batch_id,
    present: id => ({ label: batchNames.value.get(Number(id)) ?? `Batch #${id}`, icon: 'i-ph-arrows-split-bold' }),
  },
  {
    key: 'rows',
    label: 'Rows',
    icon: 'i-ph-rows-bold',
    // Unknown until the run has results, which is neither small nor not
    value: exp => exp.row_count == null ? undefined : isSmallSample(exp.row_count) ? 'small' : 'full',
    present: value => ({ label: value === 'small' ? `Under ${SMALL_SAMPLE_ROWS} rows` : `${SMALL_SAMPLE_ROWS} rows or more` }),
    compare: byOrder(['small', 'full']),
  },
  runsFilter(exp => exp.execution_count),
  failures,
  dateFilter(exp => exp.created_at),
  lastRunFilter,
])

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (experiment: Experiment) => handleViewExperiment(experiment.id),
  },
  {
    label: 'Cancel run',
    icon: 'i-ph-square-bold',
    requires: 'editor' as const,
    show: (experiment: Experiment) => ['running', 'queued'].includes(runOf(experiment.id)?.status ?? experiment.status ?? ''),
    handler: (experiment: Experiment) => handleCancelExperiment(experiment),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
    handler: (experiment: Experiment) => handleDeleteExperiments([experiment.id]),
  },
]

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

// An analysis reads one run of each experiment: the latest that ended well and kept its results.
// The experiments without one are left out, and said so
async function analyze(ids: readonly number[]) {
  const picked = (experiments.value ?? []).filter(exp => ids.includes(exp.id))
  const runs = picked.flatMap(exp => exp.latest_analyzable_execution_id ? [exp.latest_analyzable_execution_id] : [])
  if (!runs.length) {
    info('Nothing to analyze', 'Only experiments with a completed run and its results can be analyzed.')
    return
  }
  const left = picked.length - runs.length
  if (left > 0) {
    info(`${left} of ${picked.length} can’t be analyzed`, 'Only experiments with a completed run and its results can be.')
  }
  // Oldest first, as the experiment page sends them
  await navigateTo({
    path: '/analyses/new',
    query: { executions: runs.sort((a, b) => a - b).join(','), ...(picked.length === 1 ? { name: picked[0]!.name } : {}) },
  })
}

// Stopping a run can't be taken back: it asks first, as the experiment page does
function handleCancelExperiment(experiment: Experiment) {
  pendingCancel.value = experiment
  showCancelDialog.value = true
}

const cancelQueued = computed(() => !!pendingCancel.value && (runOf(pendingCancel.value.id)?.status ?? pendingCancel.value.status) === 'queued')

async function confirmCancel() {
  showCancelDialog.value = false
  if (!pendingCancel.value)
    return
  isCancelling.value = true
  const result = await cancelExperiment(pendingCancel.value.id)
  isCancelling.value = false
  if (!result.success) {
    fail('Couldn’t cancel the run')
    return
  }
  if (result.data.cancelled)
    ok('Run cancelled')
  else
    info('Nothing to cancel', 'This experiment is no longer running.')
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

  const failed: number[] = []
  for (const id of pendingDeleteIds.value) {
    const { success } = await deleteExperiment(id)
    if (!success)
      failed.push(id)
  }
  const deleted = deleteCount.value - failed.length

  if (deleted > 0) {
    if (deleted === 1)
      showDeleteSuccess('Experiment')
    else
      ok(`${deleted} experiments deleted`)
  }
  if (failed.length > 0) {
    if (failed.length === 1)
      showDeleteError('Experiment')
    else
      fail(`Couldn’t delete ${failed.length} experiments`)
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
    :error="!experiments && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UTooltip text="New experiment" :kbds="['C']" :disabled="!canEdit">
        <UIGuardedButton
          color="neutral"
          variant="soft"
          icon="i-ph-plus-bold"
          size="sm"
          @click="handleCreateExperiment"
        >
          New experiment
        </UIGuardedButton>
      </UTooltip>
    </template>

    <!-- Experiments Table -->
    <div v-if="experiments && experiments.length > 0" class="flex flex-col flex-1 min-h-0">
      <BaseDataTable
        v-model:selected="selectedIds"
        v-model:filter-state="filterState"
        v-model:group-by="groupBy"
        v-model:sort-by="sortBy"
        fill
        :data="experiments"
        :columns="columns"
        :filters="filters"
        :groups="groups"
        :sorts="sorts"
        :actions="actions"
        :loading="pending"
        :row-to="(exp: Experiment) => `/experiments/${exp.id}`"
        :row-hint="(exp: Experiment) => `#${exp.id}`"
        :selectable="canEdit"
        item-name="experiment"
        searchable
        @refresh="refresh"
      >
        <template #selection-actions>
          <UButton
            variant="ghost"
            color="neutral"
            icon="i-ph-chart-bar-bold"
            size="sm"
            @click="analyze(selectedIds)"
          >
            Analyze
          </UButton>
          <StudiesBulkMenu kind="experiment" :ids="selectedIds" />
          <UButton
            variant="ghost"
            color="error"
            icon="i-ph-trash-bold"
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
          </div>
        </template>

        <template #batch_name-cell="{ row }">
          <!-- Above the row's stretched link, so it opens the batch instead of the experiment -->
          <NuxtLink
            v-if="row.original.batch_id"
            :to="`/batches/${row.original.batch_id}`"
            class="relative z-1 inline-flex max-w-48 items-center gap-1 rounded text-sm text-toned outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
            :title="`Open batch ${row.original.batch_name}`"
          >
            <UIcon name="i-ph-arrows-split-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
            <span class="truncate">{{ row.original.batch_name }}</span>
          </NuxtLink>
          <span v-else class="text-dimmed">—</span>
        </template>

        <template #row_count-cell="{ row }">
          <div class="flex min-w-0 flex-col">
            <span>
              <UIRowCount :rows="row.original.row_count" tone="quiet" class="text-sm" />
              <!-- The progress under it counts the failed ones while the run is going -->
              <span v-if="row.original.rows_failed && runOf(row.original.id)?.status !== 'running'" class="ms-2 text-xs text-error tabular-nums">{{ row.original.rows_failed }} failed</span>
            </span>
            <UIRunProgress :run="runOf(row.original.id)" />
          </div>
        </template>

        <template #total_tokens-cell="{ row }">
          <span :title="formatCount(row.original.total_tokens)">{{ formatTokens(row.original.total_tokens) }}</span>
        </template>

        <template #total_cost_usd-cell="{ row }">
          <span :title="formatCostPrecise(row.original.total_cost_usd)">{{ formatCost(row.original.total_cost_usd) }}</span>
        </template>

        <!-- Custom cell for created_at -->
        <template #created_at-cell="{ row }">
          <span class="text-sm text-muted" :title="formatDate(row.original.created_at)">
            {{ formatRelativeDate(row.original.created_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No experiments yet"
      message="An experiment runs agents over a dataset, so you can compare outputs and analyze them."
      icon="i-ph-flask-bold"
      action-label="New experiment"
      action-to="/experiments/new"
      action-requires="editor"
      @action="handleCreateExperiment"
    />

    <BaseConfirmDialog
      v-model:open="showCancelDialog"
      :title="cancelQueued ? 'Take this run out of the queue?' : 'Stop this run?'"
      :message="cancelQueued ? 'It leaves the queue without running. You can re-run it later.' : 'The run stops now. You can re-run the experiment later.'"
      :confirm-label="cancelQueued ? 'Remove from queue' : 'Stop run'"
      variant="warning"
      :loading="isCancelling"
      @confirm="confirmCancel"
    />

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      :title="deleteCount > 1 ? `Delete ${deleteCount} experiments?` : 'Delete experiment?'"
      :message="`${deleteCount > 1 ? 'These experiments and all of their executions are deleted.' : 'The experiment and all of its executions are deleted.'} This can’t be undone.`"
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="confirmDelete"
    />
  </BasePageContent>
</template>
