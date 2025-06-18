<script setup lang="ts">
import type { CreateDatasetForm } from '~/types'

// Composables
const { datasets, pending, refresh, createDataset, deleteDataset } = useDatasets()
const { showSuccess, showError } = useNotifications()

// State
const isSubmitting = ref(false)

// Handlers
async function handleCreateDataset(formData: CreateDatasetForm) {
  isSubmitting.value = true

  try {
    const result = await createDataset(formData)

    if (result.success) {
      showSuccess('Dataset created successfully!')
    }
    else {
      showError('Error creating dataset. Please try again.')
    }
  }
  catch {
    showError('Error creating dataset. Please try again.')
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
    showSuccess('Dataset deleted successfully!')
  }
  else {
    showError('Error deleting dataset. Please try again.')
  }
}

function handleRefresh() {
  refresh()
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <!-- Create Dataset Form -->
      <DatasetsForm
        :loading="isSubmitting"
        @submit="handleCreateDataset"
      />

      <!-- Datasets List -->
      <DatasetsList
        :datasets="datasets"
        :loading="pending"
        @refresh="handleRefresh"
        @view="handleViewDataset"
        @delete="handleDeleteDataset"
      />
    </div>
  </div>
</template>
