<script setup lang="ts">
import type { Dataset, DatasetStats } from '~/types'
import type { FetchErrorKind } from '~/utils/fetchError'

// Route params
const route = useRoute()
const datasetId = computed(() => Number.parseInt(route.params.id as string))

// Composables
const { showDeleteSuccess, showDeleteError } = useStandardToast()
const { deleteDataset, getDataset, getDatasetStats } = useDatasets()
const { canEdit } = useCurrentWorkspace()

// State
const dataset = ref<Dataset | null>(null)
const datasetStats = ref<DatasetStats | null>(null)
const loading = ref(true)
const loadError = ref<FetchErrorKind | null>(null)
const showDeleteDialog = ref(false)
const isDeleting = ref(false)

// The editor stays mounted behind the other view: switching must not drop unsaved edits
const views = [
  { value: 'rows', label: 'Rows', icon: 'i-ph-rows-bold' },
  { value: 'agreement', label: 'Agreement', icon: 'i-ph-users-three-bold' },
] as const
const view = ref<(typeof views)[number]['value']>('rows')

// Computed
const { formatDate, formatRelativeDate } = useUIHelpers()

const pageTitle = computed(() => {
  return dataset.value ? dataset.value.name : 'Loading…'
})

useBreadcrumbLabel(() => dataset.value?.name)

// Set page title
useSeoMeta({
  title: pageTitle,
})

// Methods
async function loadDataset() {
  loading.value = true
  loadError.value = null
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
      dataset.value = null
      loadError.value = fetchErrorKind(datasetResult.error)
    }
  }
  catch (error) {
    console.error('Error loading dataset:', error)
    dataset.value = null
    loadError.value = 'error'
  }
  finally {
    loading.value = false
  }
}

async function handleDeleteDataset() {
  if (!dataset.value || isDeleting.value)
    return

  isDeleting.value = true
  try {
    const result = await deleteDataset(dataset.value.id)
    if (result.success) {
      showDeleteSuccess('Dataset')
      await navigateTo('/datasets')
    }
    else {
      showDeleteError('Dataset')
    }
  }
  catch (error) {
    console.error('Error deleting dataset:', error)
    showDeleteError('Dataset')
  }
  finally {
    isDeleting.value = false
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
  <!-- Fills the panel so only the rows scroll, not the page -->
  <div class="flex flex-col flex-1 min-h-0">
    <div class="flex flex-col flex-1 min-h-0">
      <!-- Loading State -->
      <BaseLoadingState v-if="loading" />

      <!-- Dataset Details -->
      <div v-else-if="dataset" class="flex flex-col flex-1 min-h-0 gap-3">
        <!-- Edit isn't available yet, so it isn't shown as a dead button -->
        <AppPageActions v-if="canEdit">
          <UDropdownMenu
            :items="[{ label: 'Delete dataset', icon: 'i-ph-trash-bold', color: 'error', onSelect: () => { showDeleteDialog = true } }]"
            :content="{ align: 'end' }"
          >
            <UButton icon="i-ph-dots-three-bold" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
          </UDropdownMenu>
        </AppPageActions>

        <!-- One line: name and description on the left, properties on the right. The rows get the space. -->
        <header class="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <div class="flex min-w-0 flex-1 items-baseline gap-x-3 basis-64">
            <h1 class="shrink-0 max-w-full truncate text-base font-semibold text-highlighted">
              {{ dataset.name }}
            </h1>
            <p v-if="dataset.description" class="min-w-0 truncate text-sm text-muted" :title="dataset.description">
              {{ dataset.description }}
            </p>
          </div>
          <dl class="flex min-w-0 flex-wrap items-baseline gap-x-5 gap-y-1 text-xs text-muted">
            <div class="flex items-baseline gap-1.5">
              <dt>Created</dt>
              <dd class="text-toned tabular-nums" :title="formatDate(dataset.created_at)">
                {{ formatRelativeDate(dataset.created_at) }}
              </dd>
            </div>
            <div class="flex min-w-0 items-baseline gap-1.5">
              <dt>File</dt>
              <dd class="min-w-0 max-w-56 truncate font-mono text-toned" :title="dataset.file_path || undefined">
                {{ dataset.file_path || 'No file' }}
              </dd>
            </div>
            <div class="flex items-baseline gap-1.5">
              <dt>Used in</dt>
              <dd class="text-toned tabular-nums">
                <template v-if="datasetStats">
                  {{ datasetStats.experiment_count }} experiment{{ datasetStats.experiment_count === 1 ? '' : 's' }}
                </template>
                <template v-else>
                  —
                </template>
              </dd>
            </div>
          </dl>
        </header>

        <UFieldGroup v-if="dataset.file_path" class="self-start">
          <UButton
            v-for="v in views"
            :key="v.value"
            :label="v.label"
            :icon="v.icon"
            :variant="view === v.value ? 'subtle' : 'outline'"
            color="neutral"
            size="xs"
            :aria-pressed="view === v.value"
            @click="() => { view = v.value }"
          />
        </UFieldGroup>

        <!-- Rows: browse, search and edit the whole file -->
        <DatasetsEditor
          v-if="dataset.file_path"
          v-show="view === 'rows'"
          class="flex-1 min-h-0"
          :dataset-id="dataset.id"
          :experiment-count="datasetStats?.experiment_count ?? null"
        />

        <!-- Agreement: how much some columns rate the rows alike. Reopened each time, so it follows saved edits -->
        <DatasetsAgreement
          v-if="dataset.file_path && view === 'agreement'"
          :key="dataset.id"
          class="flex-1 min-h-0"
          :dataset-id="dataset.id"
        />

        <BaseEmptyState
          v-if="!dataset.file_path"
          icon="i-ph-file-x-bold"
          title="No file attached"
          message="This dataset has no file yet. Create a new dataset with a CSV or JSON file to use it in experiments."
          action-label="New dataset"
          action-to="/datasets"
          action-requires="editor"
        />
      </div>

      <!-- Error State -->
      <BaseErrorState
        v-else
        :kind="loadError ?? 'not-found'"
        action-label="Back to datasets"
        action-to="/datasets"
        @retry="loadDataset()"
      />
    </div>

    <!-- Delete Confirmation Dialog -->
    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      :title="`Delete “${dataset?.name}”?`"
      message="The dataset file is removed from disk. Experiments that used it keep their results. This can’t be undone."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="handleDeleteDataset"
    />
  </div>
</template>
