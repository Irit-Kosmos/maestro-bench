<script setup lang="ts">
import type { DatasetInfo } from '~/composables/useDatasetInfo'

interface Props {
  datasetId?: number
  samplingType?: string
  samplingSize?: number
  samplingStartRow?: number
  samplingEndRow?: number
}

interface Emits {
  'update:samplingType': [value: string]
  'update:samplingSize': [value: number | undefined]
  'update:samplingStartRow': [value: number | undefined]
  'update:samplingEndRow': [value: number | undefined]
}

const props = withDefaults(defineProps<Props>(), {
  samplingType: 'all',
})

const emit = defineEmits<Emits>()

// Composables
const { fetchDatasetInfo } = useDatasetInfo()

// State
const datasetInfo = ref<DatasetInfo | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

// Computed
const samplingTypeOptions = [
  { label: 'Use all rows', value: 'all' },
  { label: 'Random sample', value: 'random' },
  { label: 'Specific row range', value: 'range' },
]

const maxRows = computed(() => datasetInfo.value?.total_rows || 0)

const isValidRange = computed(() => {
  if (props.samplingType !== 'range')
    return true
  if (!props.samplingStartRow || !props.samplingEndRow)
    return false
  return props.samplingStartRow <= props.samplingEndRow
    && props.samplingStartRow >= 1
    && props.samplingEndRow <= maxRows.value
})

const isValidSampleSize = computed(() => {
  if (props.samplingType !== 'random')
    return true
  if (!props.samplingSize)
    return false
  return props.samplingSize > 0 && props.samplingSize <= maxRows.value
})

const previewText = computed(() => {
  if (!datasetInfo.value)
    return ''

  switch (props.samplingType) {
    case 'all':
      return `All ${datasetInfo.value.total_rows} rows will be used`
    case 'random':
      return props.samplingSize
        ? `${props.samplingSize} random rows will be selected from ${datasetInfo.value.total_rows} total rows`
        : 'Random sample size not specified'
    case 'range':
      return props.samplingStartRow && props.samplingEndRow
        ? `Rows ${props.samplingStartRow} to ${props.samplingEndRow} will be used (${props.samplingEndRow - props.samplingStartRow + 1} rows total)`
        : 'Row range not specified'
    default:
      return ''
  }
})

// Methods
async function loadDatasetInfo() {
  if (!props.datasetId)
    return

  loading.value = true
  error.value = null

  try {
    const result = await fetchDatasetInfo(props.datasetId)
    if (result.success && result.data) {
      datasetInfo.value = result.data as DatasetInfo
    }
    else {
      error.value = 'Failed to load dataset information'
    }
  }
  catch (e) {
    error.value = 'Error loading dataset information'
    console.error('Error loading dataset info:', e)
  }
  finally {
    loading.value = false
  }
}

function updateSamplingType(value: string) {
  emit('update:samplingType', value)

  // Clear other values when changing type
  if (value !== 'random') {
    emit('update:samplingSize', undefined)
  }
  if (value !== 'range') {
    emit('update:samplingStartRow', undefined)
    emit('update:samplingEndRow', undefined)
  }
}

function updateSamplingSize(value: string) {
  const num = value ? Number.parseInt(value) : undefined
  emit('update:samplingSize', num)
}

function updateSamplingStartRow(value: string) {
  const num = value ? Number.parseInt(value) : undefined
  emit('update:samplingStartRow', num)
}

function updateSamplingEndRow(value: string) {
  const num = value ? Number.parseInt(value) : undefined
  emit('update:samplingEndRow', num)
}

// Watch for dataset changes
watch(() => props.datasetId, loadDatasetInfo, { immediate: true })
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center gap-3">
      <UIcon name="i-lucide-filter" class="h-5 w-5 text-primary-500" />
      <h3 class="text-lg font-semibold text-neutral-900">
        Dataset Sampling Configuration
      </h3>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="flex items-center gap-2 text-neutral-600">
      <UIcon name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
      <span class="text-sm">Loading dataset information...</span>
    </div>

    <!-- Error State -->
    <UAlert v-else-if="error" color="error" variant="soft" :title="error" />

    <!-- Configuration -->
    <div v-else-if="datasetInfo" class="space-y-4">
      <!-- Dataset Summary -->
      <UCard>
        <template #header>
          <h4 class="text-base font-medium">
            Dataset Overview
          </h4>
        </template>

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div class="text-center">
            <div class="text-2xl font-bold text-primary-600">
              {{ datasetInfo.total_rows }}
            </div>
            <div class="text-sm text-neutral-500">
              Total Rows
            </div>
          </div>
          <div class="text-center">
            <div class="text-2xl font-bold text-primary-600">
              {{ datasetInfo.total_columns }}
            </div>
            <div class="text-sm text-neutral-500">
              Columns
            </div>
          </div>
          <div class="text-center">
            <UBadge :label="datasetInfo.file_type.toUpperCase()" variant="subtle" color="info" />
            <div class="text-sm text-neutral-500 mt-1">
              File Type
            </div>
          </div>
        </div>
      </UCard>

      <div class="flex gap-8">
        <!-- Sampling Type Selection -->
        <UFormField label="Sampling Method" required>
          <USelect
            :model-value="samplingType"
            :items="samplingTypeOptions"
            class="w-60"
            @update:model-value="updateSamplingType"
          />
        </UFormField>

        <!-- Random Sample Configuration -->
        <div v-if="samplingType === 'random'" class="space-y-4">
          <UFormField
            label="Sample Size"
            required
            :error="!isValidSampleSize ? `Sample size must be between 1 and ${maxRows}` : undefined"
          >
            <UInput
              :model-value="samplingSize?.toString() || ''"
              type="number"
              :min="1"
              :max="maxRows"
              placeholder="e.g., 100"
              @update:model-value="updateSamplingSize"
            />
            <template #help>
              <span class="text-xs text-neutral-500">
                Enter the number of rows to randomly sample (max: {{ maxRows }})
              </span>
            </template>
          </UFormField>
        </div>

        <!-- Range Configuration -->
        <div v-if="samplingType === 'range'" class="space-y-4">
          <div class="flex gap-4">
            <UFormField
              label="Start Row"
              required
              :error="samplingStartRow && (samplingStartRow < 1 || samplingStartRow > maxRows) ? `Must be between 1 and ${maxRows}` : undefined"
            >
              <UInput
                :model-value="samplingStartRow?.toString() || ''"
                type="number"
                :min="1"
                :max="maxRows"
                placeholder="1"
                @update:model-value="updateSamplingStartRow"
              />
            </UFormField>

            <UFormField
              label="End Row"
              required
              :error="samplingEndRow && (!isValidRange) ? `Must be >= start row and <= ${maxRows}` : undefined"
            >
              <UInput
                :model-value="samplingEndRow?.toString() || ''"
                type="number"
                :min="samplingStartRow || 1"
                :max="maxRows"
                placeholder="100"
                @update:model-value="updateSamplingEndRow"
              />
            </UFormField>
          </div>

          <p class="text-xs text-neutral-500">
            Specify the row range to use (1-based indexing). Both start and end rows are inclusive.
          </p>
        </div>
      </div>
    </div>

    <!-- No Dataset Selected -->
    <div v-else class="text-center py-8">
      <UIcon name="i-lucide-info" class="w-8 h-8 text-neutral-400 mx-auto mb-2" />
      <p class="text-sm text-neutral-500">
        Select a dataset to configure sampling options
      </p>
    </div>
  </div>
</template>
