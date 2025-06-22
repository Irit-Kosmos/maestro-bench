<script setup lang="ts">
import type { CreateDatasetForm, Dataset } from '~/types'

// Composables
const { datasets, pending, refresh, createDataset, deleteDataset } = useDatasets()
const toast = useToast()

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
      toast.add({
        title: 'Success',
        description: 'Dataset created successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      showCreateModal.value = false
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Error creating dataset. Please try again.',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch {
    toast.add({
      title: 'Error',
      description: 'Error creating dataset. Please try again.',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
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
    toast.add({
      title: 'Success',
      description: 'Dataset deleted successfully!',
      color: 'success',
      icon: 'i-lucide:check-circle',
    })
  }
  else {
    toast.add({
      title: 'Error',
      description: 'Error deleting dataset. Please try again.',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
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
  <BasePageLayout
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
        <template #cell-created_at="{ item }">
          <span class="text-sm text-neutral-500">
            {{ new Date(item.created_at).toLocaleDateString() }}
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
  </BasePageLayout>
</template>
