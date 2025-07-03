<script setup lang="ts">
import type { Dataset } from '~/types'

interface Props {
  selectedDataset?: number
  datasets?: Dataset[] | null
}

interface Emits {
  'update:selectedDataset': [value: number | undefined]
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
  <div class="space-y-4 mt-4">
    <div class="max-w-4xl mx-auto w-full">
      <div class="mb-6">
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          Select Dataset
        </h3>
        <p class="text-sm text-neutral-600">
          Choose a dataset for your experiment. Click to select, and use the preview button to see the data structure.
        </p>
      </div>

      <!-- Datasets Grid -->
      <div v-if="datasets && datasets.length > 0" class="space-y-2">
        <div
          v-for="dataset in datasets"
          :key="dataset.id"
          class="cursor-pointer border border-neutral-200 hover:border-primary py-3 px-4 rounded-lg transition-all duration-200"
          :class="{
            'bg-primary-50 border-primary-500': selectedDataset === dataset.id,
            'bg-white': selectedDataset !== dataset.id,
          }"
          @click="selectDataset(dataset.id)"
        >
          <div class="flex items-center justify-between">
            <div class="flex-1">
              <div class="flex items-center gap-3">
                <!-- Dataset Info -->
                <div class="flex-1">
                  <h4 class="text-base font-medium text-neutral-900">
                    {{ dataset.name }}
                  </h4>
                  <p class="text-sm text-neutral-600 mt-1">
                    {{ dataset.description }}
                  </p>
                  <div class="flex items-center gap-4 mt-2">
                    <span class="text-xs text-neutral-500">
                      <UIcon name="i-lucide-calendar" class="w-3 h-3 inline mr-1" />
                      {{ new Date(dataset.created_at).toLocaleDateString() }}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Preview Button -->
            <UButton
              variant="ghost"
              :icon="expandedDataset === dataset.id ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
              @click.stop="togglePreview(dataset.id)"
            >
              Preview
            </UButton>
          </div>

          <!-- Expandable Preview Section -->
          <div
            v-if="expandedDataset === dataset.id"
            class="mt-4 pt-4 border-t border-neutral-200"
          >
            <div class="bg-neutral-50 rounded-lg p-4">
              <div class="flex items-center justify-between mb-3">
                <h5 class="text-sm font-medium text-neutral-700">
                  Dataset Preview
                </h5>
                <UBadge size="sm" variant="subtle" color="neutral">
                  Sample Data
                </UBadge>
              </div>
              <DatasetsPreview :dataset-id="dataset.id" />
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="datasets && datasets.length === 0" class="text-center py-12">
        <UIcon name="i-lucide-database-x" class="w-16 h-16 text-neutral-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          No Datasets Available
        </h3>
        <p class="text-neutral-600 mb-6">
          You need to upload datasets before creating experiments.
        </p>
        <UButton
          to="/datasets"
          icon="i-lucide-plus"
          size="lg"
        >
          Upload Dataset
        </UButton>
      </div>

      <!-- Loading State -->
      <div v-else class="text-center py-12">
        <UIcon name="i-lucide-loader-2" class="w-8 h-8 text-neutral-400 mx-auto mb-4 animate-spin" />
        <p class="text-neutral-600">
          Loading datasets...
        </p>
      </div>
    </div>
  </div>
</template>
