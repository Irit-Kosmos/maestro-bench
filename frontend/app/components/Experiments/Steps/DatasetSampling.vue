<script setup lang="ts">
interface Props {
  selectedDataset?: number
  samplingConfig: {
    sampling_type: string
    sampling_size?: number
    sampling_start_row?: number
    sampling_end_row?: number
  }
}

interface Emits {
  'update:sampling-type': [value: string]
  'update:sampling-size': [value: number | undefined]
  'update:sampling-start-row': [value: number | undefined]
  'update:sampling-end-row': [value: number | undefined]
}

const _props = defineProps<Props>()
const emit = defineEmits<Emits>()
</script>

<template>
  <div class="space-y-6 mt-4">
    <ExperimentsDatasetSamplingConfig
      v-if="selectedDataset"
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

    <div v-else class="text-center py-12">
      <UIcon name="i-lucide-arrow-left" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
      <h3 class="text-lg font-medium text-neutral-900 mb-2">
        Select a Dataset First
      </h3>
      <p class="text-neutral-600">
        Go back to the previous step to choose a dataset before configuring sampling options.
      </p>
    </div>
  </div>
</template>
