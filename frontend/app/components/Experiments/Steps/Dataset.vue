<script setup lang="ts">
import type { Dataset } from '~/types'

interface Props {
  selectedDataset?: number
  datasets?: Dataset[] | null
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
  <div class="mt-6 flex flex-col gap-8">
    <!-- Dataset Selection -->
    <section aria-labelledby="dataset-step-title" class="max-w-3xl">
      <h3 id="dataset-step-title" class="text-sm font-semibold text-highlighted">
        Dataset
      </h3>
      <p class="mt-0.5 mb-3 text-sm text-muted">
        Each row is one input for the agents. Open a preview to check the columns.
      </p>

      <!-- Native radios: arrow keys move the selection, and the checked dot doesn't rely on color -->
      <div v-if="datasets && datasets.length > 0" role="radiogroup" aria-labelledby="dataset-step-title" class="flex flex-col gap-2">
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
              :trailing-icon="expandedDataset === dataset.id ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
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
        icon="i-lucide-database"
        title="No datasets yet"
        message="Add a dataset first, then come back to create the experiment."
        action-label="New dataset"
        action-to="/datasets"
      />

      <BaseLoadingState v-else message="Loading datasets…" />
    </section>

    <!-- Sampling Configuration -->
    <section v-if="selectedDataset" aria-labelledby="sampling-step-title" class="enter-soft max-w-3xl">
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
