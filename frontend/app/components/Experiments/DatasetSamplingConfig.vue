<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { DatasetInfo } from '~/composables/useDatasetInfo'

interface Props {
  datasetId?: number
  samplingType?: string
  samplingSize?: number
  samplingStartRow?: number
  samplingEndRow?: number
  samplingSeed?: number
}

interface Emits {
  'update:samplingType': [value: string]
  'update:samplingSize': [value: number | undefined]
  'update:samplingStartRow': [value: number | undefined]
  'update:samplingEndRow': [value: number | undefined]
  'update:samplingSeed': [value: number | undefined]
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
// The sampling inputs point to the line under them, which holds the hint or what is wrong
const feedbackId = useId()

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

// pandas takes seeds from 0 to 2**32 - 1
const MAX_SEED = 2 ** 32 - 1

const seedError = computed(() => {
  const seed = props.samplingSeed
  if (props.samplingType !== 'random' || seed === undefined)
    return undefined
  return seed >= 0 && seed <= MAX_SEED
    ? undefined
    : `Seed must be a whole number between 0 and ${formatNumber(MAX_SEED)}.`
})

const samplingError = computed(() => sampleSizeError.value || rangeError.value || seedError.value)

const hint = computed(() => {
  const total = formatNumber(maxRows.value)
  if (props.samplingType === 'random') {
    const kept = props.samplingSeed === undefined
      ? 'kept for every run until you resample'
      : 'the same on every run: the same seed takes the same rows from this dataset'
    return props.samplingSize && isValidSampleSize.value
      ? `${formatNumber(props.samplingSize)} of ${total} rows, drawn at random and ${kept}.`
      : `Rows are drawn at random once, then ${kept}.`
  }
  if (props.samplingType === 'range') {
    return props.samplingStartRow && props.samplingEndRow && isValidRange.value
      ? `${formatNumber(props.samplingEndRow - props.samplingStartRow + 1)} rows, from ${formatNumber(props.samplingStartRow)} to ${formatNumber(props.samplingEndRow)}, the same on every run.`
      : 'Rows are numbered from 1; start and end are inclusive.'
  }
  return `All ${total} rows, the same on every run.`
})

// Methods
const LOAD_ERROR = 'Unable to load dataset information. Check your connection and try again.'

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
      error.value = LOAD_ERROR
    }
  }
  catch (e) {
    error.value = LOAD_ERROR
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
    emit('update:samplingSeed', undefined)
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

function updateSamplingSeed(value: string) {
  // Empty means a seed drawn at creation; anything else is a whole number
  const num = value === '' ? undefined : Number.parseInt(value)
  emit('update:samplingSeed', Number.isNaN(num) ? undefined : num)
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
      <UIcon name="i-ph-circle-notch-bold" class="size-4 animate-spin" />
      <span class="text-sm">Loading dataset information…</span>
    </div>

    <!-- Error State -->
    <UAlert
      v-else-if="error"
      color="error"
      variant="soft"
      :title="error"
      :actions="[{ label: 'Try again', color: 'neutral', variant: 'outline', size: 'xs', onClick: loadDatasetInfo }]"
    />

    <!-- Configuration -->
    <div v-else-if="datasetInfo" class="space-y-2">
      <div class="flex flex-wrap items-center gap-x-3 gap-y-2">
        <!-- Sampling Method -->
        <UTabs
          :model-value="samplingType"
          :items="samplingTypeOptions"
          :content="false"
          variant="pill"
          color="neutral"
          size="sm"
          :ui="{
            indicator: 'bg-default ring ring-default shadow-xs',
            trigger: 'data-[state=active]:text-highlighted',
          }"
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
            :aria-invalid="!!sampleSizeError"
            :aria-describedby="feedbackId"
            @update:model-value="updateSamplingSize"
          />
          <span class="text-sm text-muted tabular-nums">of {{ formatNumber(maxRows) }} rows</span>
          <UInput
            :model-value="samplingSeed?.toString() || ''"
            type="number"
            size="sm"
            class="w-36"
            :min="0"
            :max="MAX_SEED"
            placeholder="Seed (random)"
            aria-label="Sample seed"
            :color="seedError ? 'error' : undefined"
            :highlight="!!seedError"
            :aria-invalid="!!seedError"
            :aria-describedby="feedbackId"
            @update:model-value="updateSamplingSeed"
          />
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
            :aria-invalid="!!rangeError"
            :aria-describedby="feedbackId"
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
            :aria-invalid="!!rangeError"
            :aria-describedby="feedbackId"
            @update:model-value="updateSamplingEndRow"
          />
        </div>

        <!-- Dataset facts -->
        <p class="ms-auto flex items-center gap-1.5 text-xs text-muted tabular-nums">
          <span>{{ formatNumber(maxRows) }} rows</span>
          <span aria-hidden="true">·</span>
          <span>{{ datasetInfo.total_columns }} columns</span>
          <UBadge :label="datasetInfo.file_type.toUpperCase()" variant="subtle" color="neutral" size="sm" />
        </p>
      </div>

      <p
        :id="feedbackId"
        class="text-xs tabular-nums"
        :class="samplingError ? 'text-error' : 'text-muted'"
        role="status"
      >
        {{ samplingError || hint }}
      </p>
    </div>

    <!-- No Dataset Selected -->
    <div v-else class="text-center py-8">
      <UIcon name="i-ph-info-bold" class="w-8 h-8 text-dimmed mx-auto mb-2" />
      <p class="text-sm text-muted">
        Select a dataset to configure sampling options
      </p>
    </div>
  </div>
</template>
