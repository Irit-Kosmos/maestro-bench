<script setup lang="ts">
import type { CreateDatasetForm, Dataset } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import type { SortSpec } from '~/utils/sorts'
import { dateFilter } from '~/utils/filterSpecs'
import { dateSort, nameSort, textSort } from '~/utils/sortSpecs'

// Page meta
definePageMeta({
  title: 'Datasets',
})

// Fetch data directly in the page
const { data: datasets, pending, error, refresh } = await useMyLazyFetch<Dataset[]>('/datasets')

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

const filters: FilterSpec<Dataset>[] = [
  dateFilter(dataset => dataset.created_at),
]

const sorts: SortSpec<Dataset>[] = [
  nameSort(dataset => dataset.name, 'Dataset'),
  textSort('description', 'Description', 'i-ph-text-align-left-bold', dataset => dataset.description),
  dateSort(dataset => dataset.created_at),
]

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (dataset: Dataset) => handleViewDataset(dataset.id),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
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

useCreateFromQuery(handleCreateClick)
</script>

<template>
  <BasePageContent
    :loading="pending && !datasets"
    :error="!datasets && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UIGuardedButton
        color="neutral"
        variant="soft"
        icon="i-ph-plus-bold"
        size="sm"
        @click="handleCreateClick"
      >
        New dataset
      </UIGuardedButton>
    </template>

    <!-- Datasets List -->
    <div v-if="datasets && datasets.length > 0">
      <BaseDataTable
        :data="[...(datasets || [])]"
        :columns="columns"
        :filters="filters"
        :sorts="sorts"
        :actions="actions"
        :loading="pending"
        :row-to="(dataset: Dataset) => `/datasets/${dataset.id}`"
        item-name="dataset"
        searchable
        @refresh="handleRefresh"
      >
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
      title="No datasets yet"
      message="Upload a CSV or JSON file. Each row becomes one input for your experiments."
      icon="i-ph-database-bold"
      action-label="New dataset"
      action-requires="editor"
      @action="handleCreateClick"
    />

    <!-- Create Dataset Modal -->
    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      :loading="isSubmitting"
      @submit="handleCreateDataset"
    />

    <!-- Delete Confirmation Modal -->
    <BaseConfirmDialog
      v-model:open="showDeleteModal"
      title="Delete dataset?"
      :message="`“${datasetToDelete?.name}” and its file are removed. This can’t be undone.`"
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @after-leave="datasetToDelete = null"
      @confirm="handleDeleteDataset"
    />
  </BasePageContent>
</template>
