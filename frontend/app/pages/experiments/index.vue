<script setup lang="ts">
import type { Batch, Experiment } from '~/types'

// Page meta
definePageMeta({
  title: 'Experiments',
  subtitle: 'Manage and monitor your experiments',
})

// Fetch data directly in the page
const { data: experiments, pending, refresh } = await useMyLazyFetch<Experiment[]>('/experiments')

// Quick test runs (a handful of rows) crowd the list; hide them on demand, remembered per browser
const hideSmallRuns = useCookie<boolean>('experiments-hide-small-runs', { default: () => false })
const route = useRoute()
const { data: batches } = await useMyLazyFetch<Batch[]>('/batches')

// ?batch=<id> narrows the list to one batch's experiments
const ALL_BATCHES = 0
const batchFilter = computed({
  get: () => Number(route.query.batch) || ALL_BATCHES,
  set: (id: number) => navigateTo({ path: '/experiments', query: id === ALL_BATCHES ? {} : { batch: id } }, { replace: true }),
})
const batchItems = computed(() => [
  { label: 'All experiments', value: ALL_BATCHES },
  ...(batches.value ?? []).map(batch => ({ label: batch.name, value: batch.id })),
])

// Looking at one batch means looking at all of it, so small runs are only hidden in the full list
const visibleExperiments = computed(() =>
  (experiments.value ?? []).filter(exp => batchFilter.value === ALL_BATCHES
    ? !hideSmallRuns.value || !isSmallSample(exp.row_count)
    : exp.batch_id === batchFilter.value,
  ),
)

// Composables
const { deleteExperiment } = useExperiments()
const { runOf } = useLiveRuns()
useRefreshOnRunStatus(refresh)
const { formatDate, formatRelativeDate } = useUIHelpers()
const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const experimentId = ref<number | null>(null)

// Page meta
useSeoMeta({
  title: 'Experiments',
  description: 'Manage and monitor your AI agent experiments. Create, view, and analyze experiment results.',
})

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Experiment',
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
  {
    key: 'status',
    label: 'Status',
  },
  {
    key: 'created_at',
    label: 'Created',
  },
]

const actions = [
  {
    label: 'Open',
    icon: 'i-lucide-arrow-up-right',
    handler: (experiment: Experiment) => handleViewExperiment(experiment.id),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (experiment: Experiment) => handleDeleteExperiment(experiment.id),
  },
]

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleDeleteExperiment(_id: number) {
  experimentId.value = _id
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (!experimentId.value)
    return

  isDeleting.value = true

  try {
    await deleteExperiment(experimentId.value)

    // Show success toast
    const toast = useToast()
    toast.add({
      title: 'Success',
      description: 'Experiment deleted successfully',
      color: 'success',
    })

    // Close modal and reset state
    showDeleteDialog.value = false
    experimentId.value = null

    // Refresh experiments list
    await refresh()
  }
  catch {
    // Show error toast
    const toast = useToast()
    toast.add({
      title: 'Error',
      description: 'Failed to delete experiment',
      color: 'error',
    })
  }
  finally {
    isDeleting.value = false
  }
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
        fill
        :data="visibleExperiments"
        :total-count="experiments.length"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        :row-to="(exp: Experiment) => `/experiments/${exp.id}`"
        :row-hint="(exp: Experiment) => `#${exp.id}`"
        item-name="experiment"
        searchable
        @refresh="refresh"
      >
        <template #toolbar>
          <USelectMenu
            v-if="batchItems.length > 1"
            v-model="batchFilter"
            value-key="value"
            :items="batchItems"
            :search-input="{ placeholder: 'Search batches…' }"
            icon="i-lucide-split"
            size="xs"
            variant="ghost"
            color="neutral"
            class="w-44"
            aria-label="Filter by batch"
          />
          <USwitch
            v-model="hideSmallRuns"
            size="sm"
            :label="`Hide runs under ${SMALL_SAMPLE_ROWS} rows`"
            :ui="{ label: 'text-xs font-normal text-muted' }"
          />
        </template>

        <!-- Custom cell for status -->
        <template #status-cell="{ row }">
          <div class="flex items-center gap-3">
            <UIStatusBadge :status="row.original.status" />
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

    <UModal v-model:open="showDeleteDialog" title="Delete experiment?">
      <template #body>
        <p class="text-sm text-toned">
          This deletes the experiment and all of its executions. This can’t be undone.
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
            Delete experiment
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
