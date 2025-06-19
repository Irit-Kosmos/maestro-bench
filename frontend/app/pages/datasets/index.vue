<script setup lang="ts">
import type { CreateDatasetForm } from '~/types'

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
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Page Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            Datasets
          </h1>
          <p class="text-gray-500 mt-1">
            Manage your datasets and data sources
          </p>
        </div>
        <UButton
          variant="solid"
          color="primary"
          icon="i-lucide:plus"
          size="lg"
          @click="showCreateModal = true"
        >
          Create Dataset
        </UButton>
      </div>

      <!-- Datasets List -->
      <DatasetsList
        :datasets="datasets"
        :loading="pending"
        @refresh="handleRefresh"
        @view="handleViewDataset"
        @delete="handleDeleteDataset"
      />
    </div>

    <!-- Create Dataset Modal -->
    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      @submit="handleCreateDataset"
    />
  </div>
</template>
