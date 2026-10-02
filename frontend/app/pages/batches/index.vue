<script setup lang="ts">
import type { Batch } from '~/types'

definePageMeta({
  title: 'Batches',
  subtitle: 'Experiments run together with different models, prompts or temperatures',
})

useSeoMeta({
  title: 'Batches',
  description: 'Groups of experiments generated from one configuration by varying models, prompts or temperatures.',
})

const { data: batches, pending, refresh } = await useMyLazyFetch<Batch[]>('/batches')

const { deleteBatch } = useBatches()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { showDeleteSuccess, showDeleteError } = useStandardToast()

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const batchId = ref<number | null>(null)

const columns = [
  { key: 'name', label: 'Batch' },
  { key: 'experiments', label: 'Experiments' },
  { key: 'status', label: 'Status' },
  {
    key: 'dataset_name',
    label: 'Dataset',
    formatter: (_: unknown, row: Batch) => row.dataset_name || '—',
  },
  { key: 'created_at', label: 'Created' },
]

const actions = [
  {
    label: 'Open',
    icon: 'i-lucide-arrow-up-right',
    handler: (batch: Batch) => navigateTo(`/batches/${batch.id}`),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
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

// Runs are watched from the list as well: refresh while any is going
const active = computed(() => (batches.value ?? []).some(b => b.status === 'running' || b.status === 'pending'))
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    if (active.value)
      refresh()
  }, 5000)
})
onBeforeUnmount(() => clearInterval(timer))

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
  <BasePageContent :loading="pending && !batches">
    <template #before-content>
      <UTooltip text="Start from an experiment, then add a variation">
        <UButton
          color="neutral"
          variant="soft"
          icon="i-lucide-plus"
          size="sm"
          to="/experiments/new"
        >
          New batch
        </UButton>
      </UTooltip>
    </template>

    <div v-if="batches && batches.length > 0">
      <BaseDataTable
        :data="[...batches]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        :row-to="(batch: Batch) => `/batches/${batch.id}`"
        :row-hint="(batch: Batch) => `#${batch.id}`"
        item-name="batch"
        item-name-plural="batches"
        searchable
        @refresh="refresh"
      >
        <template #experiments-cell="{ row }">
          <span class="text-sm text-toned tabular-nums">{{ progress(row.original) }} done</span>
        </template>

        <template #status-cell="{ row }">
          <UIStatusBadge :status="row.original.status" />
        </template>

        <template #created_at-cell="{ row }">
          <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.created_at)">
            {{ formatRelativeDate(row.original.created_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No batches yet"
      message="A batch runs the same setup with several models, prompt versions or temperatures at once. Open an experiment and choose “Vary…”, or add a variation when you create one."
      icon="i-lucide-split"
      action-label="New experiment"
      action-to="/experiments/new"
    />

    <UModal v-model:open="showDeleteDialog" title="Delete batch?">
      <template #body>
        <p class="text-sm text-toned text-pretty">
          Only the grouping is removed. Its experiments, executions and results are kept as ordinary experiments.
        </p>
      </template>
      <template #footer>
        <div class="flex gap-3 w-full justify-end">
          <UButton variant="outline" color="neutral" @click="() => { showDeleteDialog = false }">
            Cancel
          </UButton>
          <UButton variant="solid" color="error" :loading="isDeleting" @click="confirmDelete">
            Delete batch
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
