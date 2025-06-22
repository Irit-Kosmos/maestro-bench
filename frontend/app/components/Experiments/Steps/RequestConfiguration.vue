<script setup lang="ts">
interface Props {
  selectedDataset?: number
  requestConfig: {
    columnMappings: Array<{
      id: string
      sourceColumn: string
      targetField: string
    }>
  }
  previewRequest: string
  datasetHeaders?: readonly string[]
}

interface Emits {
  addColumnMapping: []
  removeColumnMapping: [id: string]
  updateColumnMapping: [id: string, field: 'sourceColumn' | 'targetField', value: string]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Get dataset headers from props with fallback
const datasetHeaders = computed(() => props.datasetHeaders || [])

function addColumnMapping() {
  emit('addColumnMapping')
}

function removeColumnMapping(id: string) {
  emit('removeColumnMapping', id)
}

function updateColumnMapping(id: string, field: 'sourceColumn' | 'targetField', value: string) {
  emit('updateColumnMapping', id, field, value)
}
</script>

<template>
  <div class="space-y-6 mt-4">
    <div class="max-w-6xl mx-auto w-full">
      <div v-if="selectedDataset" class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <!-- Column Mapping Section -->
        <div class="space-y-6">
          <div>
            <div class="flex items-center justify-between mb-4">
              <h5 class="text-base font-medium text-neutral-900">
                Column Mappings
              </h5>
              <UButton
                size="sm"
                icon="i-lucide-plus"
                @click="addColumnMapping"
              >
                Add Mapping
              </UButton>
            </div>

            <div class="space-y-4">
              <!-- Dataset Headers Display -->
              <div class="bg-neutral-50 rounded-lg p-4">
                <h6 class="text-sm font-medium text-neutral-700 mb-3">
                  Available Dataset Columns
                </h6>
                <ExperimentsDatasetHeaders :dataset-id="selectedDataset" />
              </div>

              <!-- Column Mapping Configuration -->
              <div v-if="requestConfig.columnMappings.length > 0" class="space-y-3">
                <div
                  v-for="mapping in requestConfig.columnMappings"
                  :key="mapping.id"
                  class="flex items-center gap-3 p-3 bg-white border border-neutral-200 rounded-lg"
                >
                  <!-- Source Column Select -->
                  <div class="flex-1">
                    <USelect
                      :model-value="mapping.sourceColumn"
                      :items="datasetHeaders.map((h: string) => ({ label: h, value: h }))"
                      placeholder="Select column..."
                      size="sm"
                      class="w-full"
                      @update:model-value="(value: string) => updateColumnMapping(mapping.id, 'sourceColumn', value)"
                    />
                  </div>

                  <!-- Arrow -->
                  <UIcon name="i-lucide-arrow-right" class="text-neutral-400 flex-shrink-0" />

                  <!-- Target Field Input -->
                  <div class="flex-1">
                    <UInput
                      :model-value="mapping.targetField"
                      placeholder="Field name in request..."
                      size="sm"
                      class="w-full"
                      @update:model-value="(value: string) => updateColumnMapping(mapping.id, 'targetField', value)"
                    />
                  </div>

                  <!-- Remove Button -->
                  <UButton
                    size="sm"
                    color="error"
                    variant="ghost"
                    icon="i-lucide-trash-2"
                    @click="removeColumnMapping(mapping.id)"
                  />
                </div>
              </div>

              <!-- Empty State -->
              <div v-else class="text-center py-8 bg-neutral-50 rounded-lg border-2 border-dashed border-neutral-300">
                <UIcon name="i-lucide-arrow-right-left" class="w-8 h-8 text-neutral-400 mx-auto mb-2" />
                <p class="text-sm text-neutral-600 mb-3">
                  No column mappings configured
                </p>
                <UButton
                  size="sm"
                  icon="i-lucide-plus"
                  @click="addColumnMapping"
                >
                  Add First Mapping
                </UButton>
              </div>
            </div>
          </div>
        </div>

        <!-- Request Preview Section -->
        <div class="space-y-6">
          <div>
            <h5 class="text-base font-medium text-neutral-900 mb-4">
              MAESTRO Request Preview
            </h5>
            <div class="bg-neutral-900 rounded-lg p-4">
              <div class="flex items-center justify-between mb-3">
                <h6 class="text-sm font-medium text-neutral-300">
                  Final Request Structure
                </h6>
                <UBadge size="sm" color="primary" variant="subtle">
                  JSON
                </UBadge>
              </div>
              <pre class="text-xs text-neutral-300 whitespace-pre-wrap overflow-auto max-h-96">{{ previewRequest }}</pre>
            </div>

            <!-- Mapping Summary -->
            <div v-if="requestConfig.columnMappings.length > 0" class="mt-4 p-3 bg-blue-50 rounded-lg">
              <h6 class="text-sm font-medium text-blue-900 mb-2">
                Mapping Summary
              </h6>
              <div class="space-y-1">
                <div
                  v-for="mapping in requestConfig.columnMappings"
                  :key="mapping.id"
                  class="text-xs text-blue-700"
                >
                  <span class="font-mono">{{ mapping.sourceColumn }}</span>
                  <UIcon name="i-lucide-arrow-right" class="w-3 h-3 mx-1" />
                  <span class="font-mono">data.{{ mapping.targetField }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="text-center py-12">
        <UIcon name="i-lucide-arrow-left" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          Select a Dataset First
        </h3>
        <p class="text-neutral-600">
          Go back to previous steps to choose a dataset before configuring the request structure.
        </p>
      </div>
    </div>
  </div>
</template>
