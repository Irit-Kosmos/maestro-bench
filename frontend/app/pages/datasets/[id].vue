<script setup lang="ts">
import type { Dataset } from '~/types'

// Route params
const route = useRoute()
const datasetId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const { showError, showSuccess } = useNotifications()
const { datasets, deleteDataset } = useDatasets()

// State
const dataset = ref<Dataset | null>(null)
const loading = ref(true)
const showDeleteDialog = ref(false)

// Computed
const pageTitle = computed(() => {
  return dataset.value ? dataset.value.name : 'Loading...'
})

// Methods
async function loadDataset() {
  loading.value = true
  try {
    // Find dataset in existing data or fetch from API
    if (!datasets.value) {
      showError('No datasets data available')
      await navigateTo('/datasets')
      return
    }

    const found = datasets.value.find(ds => ds.id === datasetId.value)
    if (found) {
      dataset.value = JSON.parse(JSON.stringify(found))
    }
    else {
      // TODO: Implement API call to fetch single dataset
      showError('Dataset not found')
      await navigateTo('/datasets')
    }
  }
  catch (error) {
    console.error('Error loading dataset:', error)
    showError('Failed to load dataset')
  }
  finally {
    loading.value = false
  }
}

async function handleDeleteDataset() {
  if (!dataset.value)
    return

  try {
    const result = await deleteDataset(dataset.value.id)
    if (result.success) {
      showSuccess('Dataset deleted successfully')
      await navigateTo('/datasets')
    }
    else {
      showError('Failed to delete dataset')
    }
  }
  catch (error) {
    console.error('Error deleting dataset:', error)
    showError('Failed to delete dataset')
  }
  finally {
    showDeleteDialog.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadDataset()
})

// Watch for route changes
watch(() => route.params.id, () => {
  loadDataset()
})
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
      </div>

      <!-- Dataset Details -->
      <div v-else-if="dataset" class="space-y-8">
        <!-- Overview Card -->
        <UCard>
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Dataset Overview
            </h2>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Created
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                {{ new Date(dataset.created_at).toLocaleDateString() }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">
                File Path
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                {{ dataset.file_path || 'No file uploaded' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-gray-500">
                Status
              </dt>
              <dd class="mt-1 text-sm text-gray-900">
                <UBadge
                  :color="dataset.file_path ? 'success' : 'warning'"
                  variant="subtle"
                >
                  {{ dataset.file_path ? 'Ready' : 'Pending Upload' }}
                </UBadge>
              </dd>
            </div>
          </div>
        </UCard>

        <!-- Description -->
        <UCard>
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Description
            </h2>
          </template>

          <div class="prose max-w-none">
            <p class="text-gray-600">
              {{ dataset.description }}
            </p>
          </div>
        </UCard>

        <!-- File Information -->
        <UCard v-if="dataset.file_path">
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              File Information
            </h2>
          </template>

          <div class="space-y-4">
            <div class="bg-gray-50 rounded-lg p-4">
              <h3 class="text-lg font-medium text-gray-900 mb-2">
                File Details
              </h3>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <dt class="text-sm font-medium text-gray-500">
                    Path
                  </dt>
                  <dd class="mt-1 text-sm text-gray-900 font-mono">
                    {{ dataset.file_path }}
                  </dd>
                </div>
                <div>
                  <dt class="text-sm font-medium text-gray-500">
                    Size
                  </dt>
                  <dd class="mt-1 text-sm text-gray-900">
                    Calculating...
                  </dd>
                </div>
              </div>
            </div>

            <div class="text-sm text-gray-500">
              Note: File preview and analysis features will be implemented in future iterations.
            </div>
          </div>
        </UCard>

        <!-- Upload Section -->
        <UCard v-else>
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Upload Dataset File
            </h2>
          </template>

          <div class="space-y-4">
            <div class="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
              <UIcon name="i-lucide:upload" class="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-gray-900 mb-2">
                Upload Your Dataset
              </h3>
              <p class="text-gray-500 mb-4">
                Drag and drop your dataset file here, or click to browse
              </p>
              <UButton variant="solid" color="primary" disabled>
                Upload File (Coming Soon)
              </UButton>
            </div>
          </div>
        </UCard>

        <!-- Usage Information -->
        <UCard>
          <template #header>
            <h2 class="text-xl font-semibold text-gray-900">
              Usage in Experiments
            </h2>
          </template>

          <div class="space-y-4">
            <p class="text-gray-600">
              This dataset has been used in <strong>0</strong> experiments.
            </p>

            <div class="text-sm text-gray-500">
              Note: Experiment usage tracking will be implemented in future iterations.
            </div>
          </div>
        </UCard>
      </div>

      <!-- Error State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-gray-900 mb-2">
          Dataset Not Found
        </h3>
        <p class="text-gray-500 mb-4">
          The dataset you're looking for doesn't exist.
        </p>
        <UButton to="/datasets" variant="solid" color="primary">
          Return to Datasets
        </UButton>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <UModal v-model="showDeleteDialog">
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold text-gray-900">
            Delete Dataset
          </h2>
        </template>

        <div class="space-y-4">
          <p class="text-gray-600">
            Are you sure you want to delete "{{ dataset?.name }}"? This action cannot be undone.
          </p>

          <div class="flex gap-3 justify-end">
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
              @click="handleDeleteDataset"
            >
              Delete
            </UButton>
          </div>
        </div>
      </UCard>
    </UModal>
  </div>
</template>
