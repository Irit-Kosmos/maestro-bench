<script setup lang="ts">
import type { CreateDatasetForm, Dataset } from '~/types'

// Page meta
definePageMeta({
  title: 'Datasets',
  subtitle: 'Manage your datasets and data sources',
})

// Fetch data directly in the page
const { data: datasets, pending, refresh } = await useMyLazyFetch<Dataset[]>('/datasets')

// Composables
const { createDataset, deleteDataset } = useDatasets()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { showCreateSuccess, showCreateError, showDeleteSuccess, showDeleteError } = useStandardToast()

// Page meta
useSeoMeta({
  title: 'Datasets',
  description: 'Manage your datasets and data sources for AI agent experiments.',
})

// State
const isSubmitting = ref(false)
const showCreateModal = ref(false)
const showDeleteModal = ref(false)
const isDeleting = ref(false)
const datasetToDelete = ref<Dataset | null>(null)

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Dataset',
  },
  {
    key: 'description',
    label: 'Description',
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
    handler: (dataset: Dataset) => handleViewDataset(dataset.id),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (dataset: Dataset) => confirmDelete(dataset),
  },
]

// Handlers
async function handleCreateDataset(formData: CreateDatasetForm) {
  isSubmitting.value = true

  try {
    const result = await createDataset(formData)

    if (result.success) {
      showCreateSuccess('Dataset')
      showCreateModal.value = false
      // Refresh the datasets list
      await refresh()
    }
    else {
      showCreateError('Dataset', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  catch (error) {
    showCreateError('Dataset', error instanceof Error ? error.message : undefined)
  }
  finally {
    isSubmitting.value = false
  }
}

async function handleViewDataset(id: number) {
  await navigateTo(`/datasets/${id}`)
}

function confirmDelete(dataset: Dataset) {
  datasetToDelete.value = dataset
  showDeleteModal.value = true
}

async function handleDeleteDataset() {
  if (!datasetToDelete.value)
    return

  isDeleting.value = true
  try {
    const result = await deleteDataset(datasetToDelete.value.id)

    if (result.success) {
      showDeleteSuccess('Dataset')
      showDeleteModal.value = false
      datasetToDelete.value = null
      await refresh()
    }
    else {
      showDeleteError('Dataset', typeof result.error === 'string' ? result.error : undefined)
    }
  }
  finally {
    isDeleting.value = false
  }
}

function handleRefresh() {
  refresh()
}

function handleCreateClick() {
  showCreateModal.value = true
}
</script>

<template>
  <BasePageContent
    :loading="pending"
  >
    <template #before-content>
      <UButton
        color="neutral"
        variant="soft"
        icon="i-lucide-plus"
        size="sm"
        @click="handleCreateClick"
      >
        New dataset
      </UButton>
    </template>

    <!-- Datasets List -->
    <div v-if="datasets && datasets.length > 0">
      <BaseDataTable
        :data="[...(datasets || [])]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        :row-to="(dataset: Dataset) => `/datasets/${dataset.id}`"
        item-name="dataset"
        searchable
        @refresh="handleRefresh"
      >
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
      title="No datasets yet"
      message="Upload a CSV or JSON file. Each row becomes one input for your experiments."
      icon="i-lucide-database"
      action-label="New dataset"
      @action="handleCreateClick"
    />

    <!-- Create Dataset Modal -->
    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      @submit="handleCreateDataset"
    />

    <!-- Delete Confirmation Modal -->
    <BaseConfirmDialog
      v-model:open="showDeleteModal"
      title="Delete Dataset"
      :message="`Are you sure you want to delete &quot;${datasetToDelete?.name}&quot;? The dataset file will be removed from disk. This action cannot be undone.`"
      confirm-label="Delete Dataset"
      variant="error"
      :loading="isDeleting"
      @confirm="handleDeleteDataset"
    />
  </BasePageContent>
</template>
