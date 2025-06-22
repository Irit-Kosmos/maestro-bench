<script setup lang="ts">
import type { CreateDatasetForm, Dataset } from '~/types'

// Page meta
definePageMeta({
  title: 'Datasets',
})

// Composables
const { datasets, pending, refresh, createDataset, deleteDataset } = useDatasets()
const { showCreateSuccess, showCreateError, showDeleteSuccess, showDeleteError } = useStandardToast()

// Page meta
useSeoMeta({
  title: 'Datasets',
  description: 'Manage your datasets and data sources for AI agent experiments.',
})

// State
const isSubmitting = ref(false)
const showCreateModal = ref(false)

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Dataset Name',
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
    label: 'View',
    icon: 'i-lucide-eye',
    variant: 'ghost' as const,
    color: 'neutral' as const,
    handler: (dataset: Dataset) => handleViewDataset(dataset.id),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (dataset: Dataset) => handleDeleteDataset(dataset.id),
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

async function handleDeleteDataset(id: number) {
  // TODO: Add confirmation dialog
  const result = await deleteDataset(id)

  if (result.success) {
    showDeleteSuccess('Dataset')
  }
  else {
    showDeleteError('Dataset', typeof result.error === 'string' ? result.error : undefined)
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
    title="Datasets"
    subtitle="Manage your datasets and data sources"
    :loading="pending"
  >
    <template #actions>
      <UButton
        variant="solid"
        color="primary"
        icon="i-lucide:plus"
        size="lg"
        @click="handleCreateClick"
      >
        Create Dataset
      </UButton>
    </template>

    <!-- Datasets List -->
    <div v-if="datasets && datasets.length > 0">
      <BaseDataTable
        :data="[...(datasets || [])]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        title="All Datasets"
        searchable
        @refresh="handleRefresh"
      >
        <!-- Custom cell for created_at -->
        <template #created_at-cell="{ row }">
          <span class="text-sm text-neutral-500">
            {{ new Date(row.original.created_at).toLocaleDateString() }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No datasets yet"
      message="Get started by creating your first dataset for experiments."
      icon="i-lucide:database"
      action-label="Create Your First Dataset"
      @action="handleCreateClick"
    />

    <!-- Create Dataset Modal -->
    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      @submit="handleCreateDataset"
    />
  </BasePageContent>
</template>
