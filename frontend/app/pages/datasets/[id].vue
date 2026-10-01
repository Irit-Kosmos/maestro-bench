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
const { formatDate, formatRelativeDate } = useUIHelpers()

const pageTitle = computed(() => {
  return dataset.value ? dataset.value.name : 'Loading...'
})

useBreadcrumbLabel(() => dataset.value?.name)

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
    <div class="pb-6">
      <!-- Loading State -->
      <BaseLoadingState v-if="loading" />

      <!-- Dataset Details -->
      <div v-else-if="dataset" class="flex flex-col gap-5">
        <!-- Edit isn't available yet, so it isn't shown as a dead button -->
        <AppPageActions>
          <UDropdownMenu
            :items="[{ label: 'Delete dataset', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => { showDeleteDialog = true } }]"
            :content="{ align: 'end' }"
          >
            <UButton icon="i-lucide-ellipsis" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
          </UDropdownMenu>
        </AppPageActions>

        <div>
          <h1 class="text-xl font-semibold text-highlighted text-balance">
            {{ dataset.name }}
          </h1>
          <p v-if="dataset.description" class="mt-0.5 text-sm text-muted max-w-prose">
            {{ dataset.description }}
          </p>
        </div>
        <!-- Properties -->
        <dl class="flex flex-wrap gap-x-8 gap-y-3 text-sm">
          <div>
            <dt class="text-xs text-muted">
              Created
            </dt>
            <dd class="mt-0.5 text-highlighted tabular-nums" :title="formatDate(dataset.created_at)">
              {{ formatRelativeDate(dataset.created_at) }}
            </dd>
          </div>
          <div class="min-w-0">
            <dt class="text-xs text-muted">
              File
            </dt>
            <dd class="mt-0.5 text-highlighted font-mono text-xs leading-5 truncate max-w-xs" :title="dataset.file_path || undefined">
              {{ dataset.file_path || 'No file' }}
            </dd>
          </div>
          <div>
            <dt class="text-xs text-muted">
              Used in
            </dt>
            <dd class="mt-0.5 text-highlighted tabular-nums">
              <template v-if="datasetStats">
                {{ datasetStats.experiment_count }} experiment{{ datasetStats.experiment_count === 1 ? '' : 's' }}
              </template>
              <template v-else>
                —
              </template>
            </dd>
          </div>
        </dl>

        <USeparator />

        <!-- Preview -->
        <DatasetsPreview v-if="dataset.file_path" :dataset-id="dataset.id" />

        <BaseEmptyState
          v-else
          icon="i-lucide-file-x"
          title="No file attached"
          message="This dataset has no file yet. Create a new dataset with a CSV or JSON file to use it in experiments."
          action-label="New dataset"
          action-to="/datasets"
        />
      </div>

      <!-- Error State -->
      <BaseErrorState
        v-else
        title="Dataset not found"
        message="It may have been deleted. Pick another one from the list."
        action-label="Back to datasets"
        action-to="/datasets"
      />
    </div>

    <!-- Delete Confirmation Dialog -->
    <UModal
      v-model:open="showDeleteDialog"
      :title="`Delete “${dataset?.name}”?`"
      description="The dataset file is removed from disk. Experiments that used it keep their results. This can’t be undone."
    >
      <template #footer>
        <div class="flex w-full gap-2 justify-end">
          <UButton
            variant="outline"
            color="neutral"
            @click="() => { showDeleteDialog = false }"
          >
            Cancel
          </UButton>
          <UButton
            variant="solid"
            color="error"
            @click="handleDeleteDataset"
          >
            Delete dataset
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
