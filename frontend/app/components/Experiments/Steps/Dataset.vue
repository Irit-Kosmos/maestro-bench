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
    sampling_seed?: number
  }
}

interface Emits {
  'update:selectedDataset': [value: number | undefined]
  'update:sampling-type': [value: string]
  'update:sampling-size': [value: number | undefined]
  'update:sampling-start-row': [value: number | undefined]
  'update:sampling-end-row': [value: number | undefined]
  'update:sampling-seed': [value: number | undefined]
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

// Once one is chosen, only it is shown: the others come back with "Change"
const choosing = ref(false)
const chosen = computed(() => choosing.value ? undefined : datasets.value.find(d => d.id === selectedDataset.value))
const listRef = ref<HTMLElement | null>(null)

async function change() {
  choosing.value = true
  await nextTick()
  listRef.value?.querySelector<HTMLInputElement>('input[type="radio"]:checked')?.focus()
}

// A click picks and folds the list; the arrow keys only move the choice, so the list stays until "Done"
let pointerPick = false
function markPointerPick() {
  pointerPick = true
}

// Clicking the one already chosen changes nothing, but still folds the list
function keepCurrent(datasetId: number) {
  if (pointerPick && datasetId === selectedDataset.value) {
    choosing.value = false
    pointerPick = false
  }
}

function selectDataset(datasetId: number) {
  emit('update:selectedDataset', datasetId)
  choosing.value = !pointerPick
  pointerPick = false
}

function togglePreview(datasetId: number) {
  expandedDataset.value = expandedDataset.value === datasetId ? null : datasetId
}
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- The chosen dataset, on its own -->
    <div v-if="chosen" class="rounded-lg border border-default">
      <div class="flex items-center gap-3 px-4 py-1.5">
        <UIcon name="i-ph-database-bold" class="size-4 shrink-0 text-muted" aria-hidden="true" />
        <span class="flex min-w-0 flex-1 flex-col py-1 sm:flex-row sm:items-baseline sm:gap-3">
          <span class="shrink-0 text-sm font-medium text-highlighted">{{ chosen.name }}</span>
          <span v-if="chosen.description" class="truncate text-sm text-muted" :title="chosen.description">{{ chosen.description }}</span>
        </span>
        <UButton
          variant="ghost"
          color="neutral"
          size="sm"
          :trailing-icon="expandedDataset === chosen.id ? 'i-ph-caret-up-bold' : 'i-ph-caret-down-bold'"
          :aria-expanded="expandedDataset === chosen.id"
          :aria-controls="`dataset-preview-${chosen.id}`"
          @click="togglePreview(chosen.id)"
        >
          Preview
        </UButton>
        <UButton variant="ghost" color="neutral" size="sm" icon="i-ph-repeat-bold" @click="change">
          Change
        </UButton>
      </div>
      <div
        v-if="expandedDataset === chosen.id"
        :id="`dataset-preview-${chosen.id}`"
        class="enter-soft border-t border-default px-4 py-4"
      >
        <DatasetsPreview :dataset-id="chosen.id" />
      </div>
    </div>

    <!-- Dataset Selection -->
    <div v-else ref="listRef">
      <!-- Native radios: arrow keys move the selection, and the checked dot doesn't rely on color -->
      <div v-if="datasets && datasets.length > 0" role="radiogroup" aria-labelledby="dataset-title" class="flex flex-col gap-1.5">
        <div
          v-for="dataset in datasets"
          :key="dataset.id"
          class="rounded-lg border"
          :class="selectedDataset === dataset.id ? 'border-primary bg-primary/5' : 'border-default hover:border-accented'"
        >
          <div class="flex items-center gap-3 px-4 py-1.5">
            <label class="flex flex-1 items-center gap-3 min-w-0 cursor-pointer" @pointerdown="markPointerPick" @click="keepCurrent(dataset.id)">
              <input
                type="radio"
                name="dataset"
                :value="dataset.id"
                :checked="selectedDataset === dataset.id"
                class="size-4 shrink-0 accent-(--ui-primary) cursor-pointer"
                @change="selectDataset(dataset.id)"
              >
              <span class="flex min-w-0 flex-col sm:flex-row sm:items-baseline sm:gap-3 py-1">
                <span class="shrink-0 text-sm font-medium text-highlighted">{{ dataset.name }}</span>
                <span v-if="dataset.description" class="truncate text-sm text-muted" :title="dataset.description">{{ dataset.description }}</span>
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

      <div v-if="datasets.length > 0 && (canEdit || selectedDataset)" class="mt-2 flex items-center justify-between gap-2">
        <UButton
          v-if="canEdit"
          color="neutral"
          variant="ghost"
          size="sm"
          icon="i-ph-plus-bold"
          @click="() => { showCreateModal = true }"
        >
          New dataset
        </UButton>
        <UButton
          v-if="selectedDataset"
          color="neutral"
          variant="outline"
          size="sm"
          class="ms-auto"
          @click="() => { choosing = false }"
        >
          Done
        </UButton>
      </div>
    </div>

    <DatasetsCreateDatasetModal
      v-model:open="showCreateModal"
      :loading="creating"
      @submit="handleCreate"
    />

    <!-- Sampling Configuration -->
    <section v-if="selectedDataset" aria-labelledby="sampling-step-title" class="enter-soft">
      <h3 id="sampling-step-title" class="mb-2 text-sm font-medium text-highlighted">
        Rows to run on
      </h3>

      <ExperimentsDatasetSamplingConfig
        :dataset-id="selectedDataset"
        :sampling-type="samplingConfig.sampling_type"
        :sampling-size="samplingConfig.sampling_size"
        :sampling-start-row="samplingConfig.sampling_start_row"
        :sampling-end-row="samplingConfig.sampling_end_row"
        :sampling-seed="samplingConfig.sampling_seed"
        @update:sampling-type="(value: string) => emit('update:sampling-type', value)"
        @update:sampling-size="(value: number | undefined) => emit('update:sampling-size', value)"
        @update:sampling-start-row="(value: number | undefined) => emit('update:sampling-start-row', value)"
        @update:sampling-end-row="(value: number | undefined) => emit('update:sampling-end-row', value)"
        @update:sampling-seed="(value: number | undefined) => emit('update:sampling-seed', value)"
      />
    </section>
  </div>
</template>
