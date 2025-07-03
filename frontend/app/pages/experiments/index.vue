<script setup lang="ts">
import type { Experiment } from '~/types'

// Page meta
definePageMeta({
  title: 'Experiments',
})

// Composables
const { experiments, pending, refresh, deleteExperiment } = useExperiments()
const { formatDate } = useUIHelpers()
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
    formatter: (value: string, row: Experiment) => `${value} (ID: ${row.id})`,
  },
  {
    key: 'dataset',
    label: 'Dataset',
    formatter: (_: any, row: Experiment) => row.dataset?.name || 'Unknown',
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
    label: 'View',
    icon: 'i-lucide-eye',
    variant: 'ghost' as const,
    color: 'neutral' as const,
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
    title="Experiments"
    subtitle="Manage and monitor your experiments"
    :loading="pending"
  >
    <template #actions>
      <UButton
        variant="solid"
        color="primary"
        icon="i-lucide:plus"
        size="lg"
        @click="handleCreateExperiment"
      >
        Create Experiment
      </UButton>
    </template>

    <!-- Experiments Table -->
    <div v-if="experiments && experiments.length > 0">
      <BaseDataTable
        :data="[...(experiments || [])]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        title="All Experiments"
        searchable
        @refresh="refresh"
      >
        <!-- Custom cell for status -->
        <template #status-cell="{ row }">
          <UIStatusBadge :status="row.original.status" />
        </template>

        <!-- Custom cell for created_at -->
        <template #created_at-cell="{ row }">
          <span class="text-sm text-neutral-500">
            {{ formatDate(row.original.created_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No experiments yet"
      message="Get started by creating your first experiment to test your agent teams."
      icon="i-lucide:flask-conical"
      action-label="Create Your First Experiment"
      action-to="/experiments/new"
      @action="handleCreateExperiment"
    />

    <UModal v-model:open="showDeleteDialog" title="Delete Experiment">
      <template #body>
        <p class="text-neutral-600">
          Are you sure you want to delete this experiment? This action cannot be undone.
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
            @click="confirmDelete"
          >
            Delete
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
