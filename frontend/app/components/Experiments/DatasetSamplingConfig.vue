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
  { label: 'All rows', value: 'all' },
  { label: 'Random sample', value: 'random' },
  { label: 'Row range', value: 'range' },
]

const maxRows = computed(() => datasetInfo.value?.total_rows || 0)

function formatNumber(value: number) {
  return value.toLocaleString('en-US')
}

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

const sampleSizeError = computed(() => {
  if (props.samplingType !== 'random' || !props.samplingSize || isValidSampleSize.value)
    return undefined
  return `Sample size must be between 1 and ${formatNumber(maxRows.value)}.`
})

const rangeError = computed(() => {
  if (props.samplingType !== 'range')
    return undefined
  const { samplingStartRow: start, samplingEndRow: end } = props
  if (start && (start < 1 || start > maxRows.value))
    return `Start row must be between 1 and ${formatNumber(maxRows.value)}.`
  if (end && !isValidRange.value)
    return `End row must be at least the start row and at most ${formatNumber(maxRows.value)}.`
  return undefined
})

const samplingError = computed(() => sampleSizeError.value || rangeError.value)

const hint = computed(() => {
  const total = formatNumber(maxRows.value)
  if (props.samplingType === 'random') {
    return props.samplingSize && isValidSampleSize.value
      ? `${formatNumber(props.samplingSize)} of ${total} rows, drawn at random.`
      : 'Rows are drawn at random each time the experiment runs.'
  }
  if (props.samplingType === 'range') {
    return props.samplingStartRow && props.samplingEndRow && isValidRange.value
      ? `${formatNumber(props.samplingEndRow - props.samplingStartRow + 1)} rows, from ${formatNumber(props.samplingStartRow)} to ${formatNumber(props.samplingEndRow)}.`
      : 'Rows are numbered from 1; start and end are inclusive.'
  }
  return `All ${total} rows will be used.`
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
  <div>
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center gap-2 text-toned">
      <UIcon name="i-lucide-loader-2" class="w-4 h-4 animate-spin" />
      <span class="text-sm">Loading dataset information...</span>
    </div>

    <!-- Error State -->
    <UAlert v-else-if="error" color="error" variant="soft" :title="error" />

    <!-- Configuration -->
    <div v-else-if="datasetInfo" class="space-y-2">
      <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
        <!-- Sampling Method -->
        <UTabs
          :model-value="samplingType"
          :items="samplingTypeOptions"
          :content="false"
          variant="pill"
          size="sm"
          aria-label="Sampling method"
          @update:model-value="(value) => updateSamplingType(String(value))"
        />

        <!-- Random Sample Configuration -->
        <div v-if="samplingType === 'random'" class="flex items-center gap-2">
          <UInput
            :model-value="samplingSize?.toString() || ''"
            type="number"
            size="sm"
            class="w-28"
            :min="1"
            :max="maxRows"
            placeholder="e.g. 100"
            aria-label="Sample size"
            :color="sampleSizeError ? 'error' : undefined"
            :highlight="!!sampleSizeError"
            @update:model-value="updateSamplingSize"
          />
          <span class="text-sm text-muted tabular-nums">of {{ formatNumber(maxRows) }} rows</span>
        </div>

        <!-- Range Configuration -->
        <div v-else-if="samplingType === 'range'" class="flex items-center gap-2">
          <UInput
            :model-value="samplingStartRow?.toString() || ''"
            type="number"
            size="sm"
            class="w-28"
            :min="1"
            :max="maxRows"
            placeholder="From"
            aria-label="Start row"
            :color="rangeError ? 'error' : undefined"
            :highlight="!!rangeError"
            @update:model-value="updateSamplingStartRow"
          />
          <span class="text-sm text-muted">to</span>
          <UInput
            :model-value="samplingEndRow?.toString() || ''"
            type="number"
            size="sm"
            class="w-28"
            :min="samplingStartRow || 1"
            :max="maxRows"
            placeholder="To"
            aria-label="End row"
            :color="rangeError ? 'error' : undefined"
            :highlight="!!rangeError"
            @update:model-value="updateSamplingEndRow"
          />
        </div>

        <!-- Dataset facts -->
        <p class="ml-auto flex items-center gap-1.5 text-xs text-muted tabular-nums">
          <span>{{ formatNumber(maxRows) }} rows</span>
          <span aria-hidden="true">·</span>
          <span>{{ datasetInfo.total_columns }} columns</span>
          <UBadge :label="datasetInfo.file_type.toUpperCase()" variant="subtle" color="neutral" size="sm" />
        </p>
      </div>

      <p
        class="text-xs tabular-nums"
        :class="samplingError ? 'text-error' : 'text-muted'"
        :role="samplingError ? 'alert' : undefined"
      >
        {{ samplingError || hint }}
      </p>
    </div>

    <!-- No Dataset Selected -->
    <div v-else class="text-center py-8">
      <UIcon name="i-lucide-info" class="w-8 h-8 text-dimmed mx-auto mb-2" />
      <p class="text-sm text-muted">
        Select a dataset to configure sampling options
      </p>
    </div>
  </div>
</template>
