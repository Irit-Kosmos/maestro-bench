<script setup lang="ts">
import type { CreateDatasetForm, Dataset } from '~/types'

interface Props {
  selectedDataset?: number
  datasets?: Dataset[] | null
  /** Reloads the datasets, so one created here can be picked */
  refreshDatasets?: () => Promise<void>
  samplingConfig: {
    sampling_type: string
    sampling_size?: number
    sampling_start_row?: number
    sampling_end_row?: number
  }
}

interface Emits {
  'update:selectedDataset': [value: number | undefined]
  'update:sampling-type': [value: string]
  'update:sampling-size': [value: number | undefined]
  'update:sampling-start-row': [value: number | undefined]
  'update:sampling-end-row': [value: number | undefined]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { canEdit } = useCurrentWorkspace()
const { createDataset } = useDatasets()
const { showCreateSuccess, showCreateError } = useStandardToast()

// A dataset created here is picked right away, so the form never loses its place
const showCreateModal = ref(false)
const creating = ref(false)
async function handleCreate(form: CreateDatasetForm) {
  creating.value = true
  const result = await createDataset(form)
  creating.value = false
  if (!result.success) {
    showCreateError('Dataset', result.error)
    return
  }
  showCreateModal.value = false
  showCreateSuccess('Dataset')
  await props.refreshDatasets?.()
  emit('update:selectedDataset', result.data.id)
}

// Get datasets from props
const datasets = computed(() => props.datasets || [])

// Track which dataset preview is expanded
const expandedDataset = ref<number | null>(null)

// Get selected dataset from props
const selectedDataset = computed(() => props.selectedDataset)

function selectDataset(datasetId: number) {
  emit('update:selectedDataset', datasetId)
}

function togglePreview(datasetId: number) {
  expandedDataset.value = expandedDataset.value === datasetId ? null : datasetId
}
</script>

<template>
  <div class="flex flex-col gap-8">
    <!-- Dataset Selection -->
    <div>
      <!-- Native radios: arrow keys move the selection, and the checked dot doesn't rely on color -->
      <div v-if="datasets && datasets.length > 0" role="radiogroup" aria-labelledby="dataset-title" class="flex flex-col gap-2">
        <div
          v-for="dataset in datasets"
          :key="dataset.id"
          class="rounded-lg border"
          :class="selectedDataset === dataset.id ? 'border-primary bg-primary/5' : 'border-default hover:border-accented'"
        >
          <div class="flex items-center gap-3 px-4 py-3">
            <label class="flex flex-1 items-start gap-3 min-w-0 cursor-pointer">
              <input
                type="radio"
                name="dataset"
                :value="dataset.id"
                :checked="selectedDataset === dataset.id"
                class="mt-0.5 size-4 shrink-0 accent-(--ui-primary) cursor-pointer"
                @change="selectDataset(dataset.id)"
              >
              <span class="min-w-0">
                <span class="block text-sm font-medium text-highlighted">{{ dataset.name }}</span>
                <span v-if="dataset.description" class="block mt-0.5 text-sm text-muted text-pretty">{{ dataset.description }}</span>
              </span>
            </label>

            <UButton
              variant="ghost"
              color="neutral"
              size="sm"
              :trailing-icon="expandedDataset === dataset.id ? 'i-ph-caret-up-bold' : 'i-ph-caret-down-bold'"
              :aria-expanded="expandedDataset === dataset.id"
              :aria-controls="`dataset-preview-${dataset.id}`"
              @click="togglePreview(dataset.id)"
            >
              Preview
            </UButton>
          </div>

          <div
            v-if="expandedDataset === dataset.id"
            :id="`dataset-preview-${dataset.id}`"
            class="enter-soft border-t border-default px-4 py-4"
          >
            <DatasetsPreview :dataset-id="dataset.id" />
          </div>
        </div>
      </div>

      <BaseEmptyState
        v-else-if="datasets && datasets.length === 0"
        icon="i-ph-database-bold"
        title="No datasets yet"
        message="Upload a CSV or JSON file. Each row becomes one input for the experiment."
        action-label="New dataset"
        action-requires="editor"
        @action="() => { showCreateModal = true }"
      />

      <BaseLoadingState v-else message="Loading datasets…" />

      <UButton
        v-if="canEdit && datasets.length > 0"
        color="neutral"
        variant="ghost"
        size="sm"
        icon="i-ph-plus-bold"
        class="mt-2"
        @click="() => { showCreateModal = true }"
      >
        New dataset
      </UButton>
    </div>

    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      :loading="creating"
      @submit="handleCreate"
    />

    <!-- Sampling Configuration -->
    <section v-if="selectedDataset" aria-labelledby="sampling-step-title" class="enter-soft">
      <h3 id="sampling-step-title" class="text-sm font-semibold text-highlighted">
        Sampling
      </h3>
      <p class="mt-0.5 mb-3 text-sm text-muted">
        Choose which rows this experiment runs on.
      </p>

      <ExperimentsDatasetSamplingConfig
        :dataset-id="selectedDataset"
        :sampling-type="samplingConfig.sampling_type"
        :sampling-size="samplingConfig.sampling_size"
        :sampling-start-row="samplingConfig.sampling_start_row"
        :sampling-end-row="samplingConfig.sampling_end_row"
        @update:sampling-type="(value: string) => emit('update:sampling-type', value)"
        @update:sampling-size="(value: number | undefined) => emit('update:sampling-size', value)"
        @update:sampling-start-row="(value: number | undefined) => emit('update:sampling-start-row', value)"
        @update:sampling-end-row="(value: number | undefined) => emit('update:sampling-end-row', value)"
      />
    </section>
  </div>
</template>
