<script setup lang="ts">
import type { Dataset, DatasetStats } from '~/types'

// Route params
const route = useRoute()
const datasetId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const toast = useToast()
const { deleteDataset, getDataset, getDatasetStats } = useDatasets()

// State
const dataset = ref<Dataset | null>(null)
const datasetStats = ref<DatasetStats | null>(null)
const loading = ref(true)
const showDeleteDialog = ref(false)

// Computed
const pageTitle = computed(() => {
  return dataset.value ? dataset.value.name : 'Loading...'
})

// Set page title
useSeoMeta({
  title: pageTitle,
})

// Methods
async function loadDataset() {
  loading.value = true
  try {
    // Fetch dataset directly by ID
    const datasetResult = await getDataset(datasetId.value)
    if (datasetResult.success && datasetResult.data) {
      dataset.value = datasetResult.data

      // Fetch dataset stats including experiment count
      const statsResult = await getDatasetStats(datasetId.value)
      if (statsResult.success && statsResult.data) {
        datasetStats.value = statsResult.data
      }
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Dataset not found',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
      await navigateTo('/datasets')
    }
  }
  catch (error) {
    console.error('Error loading dataset:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to load dataset',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
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
      toast.add({
        title: 'Success',
        description: 'Dataset deleted successfully',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      await navigateTo('/datasets')
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to delete dataset',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch (error) {
    console.error('Error deleting dataset:', error)
    toast.add({
      title: 'Error',
      description: 'Failed to delete dataset',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
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
      <div v-else-if="dataset" class="space-y-6">
        <!-- Dataset Header -->
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-neutral-900">
              {{ dataset.name }}
            </h1>
            <p class="mt-2 text-neutral-600">
              {{ dataset.description }}
            </p>
          </div>
          <div class="flex items-center gap-3">
            <UButton
              variant="outline"
              color="neutral"
              icon="i-lucide:edit"
              size="sm"
              disabled
            >
              Edit
            </UButton>
            <UButton
              variant="outline"
              color="error"
              icon="i-lucide:trash-2"
              size="sm"
              @click="showDeleteDialog = true"
            >
              Delete
            </UButton>
          </div>
        </div>
        <!-- Overview Card -->
        <UCard>
          <template #header>
            <h2 class="text-lg font-semibold text-neutral-900">
              Overview
            </h2>
          </template>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <dt class="text-sm font-medium text-neutral-500">
                Created
              </dt>
              <dd class="mt-1 text-sm text-neutral-900">
                {{ new Date(dataset.created_at).toLocaleDateString() }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500">
                File Path
              </dt>
              <dd class="mt-1 text-sm text-neutral-900 font-mono truncate" :title="dataset.file_path">
                {{ dataset.file_path || 'No file uploaded' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500">
                File Type
              </dt>
              <dd class="mt-1 text-sm text-neutral-900">
                {{ dataset.file_path ? dataset.file_path.split('.').pop()?.toUpperCase() || 'Unknown' : 'N/A' }}
              </dd>
            </div>
            <div>
              <dt class="text-sm font-medium text-neutral-500">
                Status
              </dt>
              <dd class="mt-1 text-sm text-neutral-900">
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

        <!-- Dataset Preview -->
        <UCard v-if="dataset.file_path">
          <template #header>
            <h2 class="text-lg font-semibold text-neutral-900">
              Dataset Preview
            </h2>
          </template>

          <DatasetsPreview :dataset-id="dataset.id" />
        </UCard>

        <!-- Upload Section -->
        <UCard v-else>
          <template #header>
            <h2 class="text-lg font-semibold text-neutral-900">
              Upload Dataset File
            </h2>
          </template>

          <div class="border-2 border-dashed border-neutral-300 rounded-lg p-8 text-center">
            <UIcon name="i-lucide:upload" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-neutral-900 mb-2">
              Upload Your Dataset
            </h3>
            <p class="text-neutral-500 mb-4">
              Drag and drop your dataset file here, or click to browse
            </p>
            <UButton variant="solid" color="primary" disabled>
              <UIcon name="i-lucide:upload" class="w-4 h-4 mr-2" />
              Upload File (Coming Soon)
            </UButton>
          </div>
        </UCard>

        <!-- Usage Information -->
        <UCard>
          <template #header>
            <h2 class="text-lg font-semibold text-neutral-900">
              Usage in Experiments
            </h2>
          </template>

          <div class="flex items-center justify-between">
            <div>
              <p class="text-sm text-neutral-600">
                This dataset has been used in
                <span class="font-semibold text-neutral-900">
                  {{ datasetStats?.experiment_count ?? 0 }}
                </span> experiments.
              </p>
              <p v-if="!datasetStats" class="text-xs text-neutral-500 mt-1">
                Loading experiment count...
              </p>
            </div>
            <UButton
              variant="outline"
              color="neutral"
              size="sm"
              disabled
            >
              View Experiments
            </UButton>
          </div>
        </UCard>
      </div>

      <!-- Error State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide:alert-circle" class="w-12 h-12 text-red-500 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          Dataset Not Found
        </h3>
        <p class="text-neutral-500 mb-4">
          The dataset you're looking for doesn't exist.
        </p>
        <UButton to="/datasets" variant="solid" color="primary">
          Return to Datasets
        </UButton>
      </div>
    </div>

    <!-- Delete Confirmation Dialog -->
    <UModal
      v-model:open="showDeleteDialog"
      title="Delete Dataset"
      :description="`Are you sure you want to delete &quot;${dataset?.name}&quot;? This action cannot be undone.`"
    >
      <template #footer>
        <div class="flex w-full gap-2 justify-end">
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
      </template>
    </UModal>
  </div>
</template>
