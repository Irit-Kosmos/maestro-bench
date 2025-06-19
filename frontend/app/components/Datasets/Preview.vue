<script setup lang="ts">
interface Props {
  datasetId?: number | null
  autoLoad?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  datasetId: null,
  autoLoad: true,
})

const {
  preview,
  loading,
  error,
  fileInfo,
  displayHeaders,
  sampleRows,
  loadPreview,
  clearPreview,
} = useDatasetPreview()

// Watch for dataset ID changes and auto-load if enabled
watch(
  () => props.datasetId,
  (newId) => {
    if (newId && props.autoLoad) {
      loadPreview(newId)
    }
    else if (!newId) {
      clearPreview()
    }
  },
  { immediate: true },
)

// Expose methods for manual control
defineExpose({
  loadPreview: () => props.datasetId ? loadPreview(props.datasetId) : null,
  clearPreview,
})

// Helper function to format cell values
function formatCellValue(value: any): string {
  if (value === null || value === undefined) {
    return '-'
  }

  if (typeof value === 'object') {
    return JSON.stringify(value)
  }

  return String(value)
}
</script>

<template>
  <div class="dataset-preview">
    <!-- Loading State -->
    <div v-if="loading" class="flex items-center justify-center py-8">
      <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
      <span class="ml-3 text-gray-600">Loading dataset preview...</span>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-lg p-4">
      <div class="flex items-center">
        <svg class="h-5 w-5 text-red-400" fill="currentColor" viewBox="0 0 20 20">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
        </svg>
        <span class="ml-2 text-red-800 font-medium">Failed to load preview</span>
      </div>
      <p class="mt-2 text-red-700">
        {{ error }}
      </p>
    </div>

    <!-- Preview Content -->
    <div v-else-if="preview" class="space-y-4">
      <!-- File Info -->
      <div class="bg-gray-50 rounded-lg p-4">
        <h3 class="text-lg font-semibold text-gray-900 mb-2">
          Dataset Information
        </h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="font-medium text-gray-600">File Type:</span>
            <span class="ml-2 text-gray-900">{{ fileInfo?.type }}</span>
          </div>
          <div>
            <span class="font-medium text-gray-600">Rows:</span>
            <span class="ml-2 text-gray-900">{{ fileInfo?.rows }}</span>
          </div>
          <div>
            <span class="font-medium text-gray-600">Columns:</span>
            <span class="ml-2 text-gray-900">{{ fileInfo?.columns }}</span>
          </div>
          <div>
            <span class="font-medium text-gray-600">Sample:</span>
            <span class="ml-2 text-gray-900">{{ sampleRows.length }} rows</span>
          </div>
        </div>
      </div>

      <!-- Headers -->
      <div>
        <h4 class="text-md font-semibold text-gray-900 mb-2">
          Column Headers
        </h4>
        <div class="flex flex-wrap gap-2">
          <span
            v-for="header in displayHeaders"
            :key="header.key"
            class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
          >
            {{ header.label }}
          </span>
        </div>
      </div>

      <!-- Sample Data Table -->
      <div v-if="sampleRows.length > 0">
        <h4 class="text-md font-semibold text-gray-900 mb-2">
          Sample Data (First 5 rows)
        </h4>
        <div class="overflow-x-auto border border-gray-200 rounded-lg">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th
                  v-for="header in displayHeaders"
                  :key="header.key"
                  class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
                >
                  {{ header.label }}
                </th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(row, index) in sampleRows" :key="index" class="hover:bg-gray-50">
                <td
                  v-for="header in displayHeaders"
                  :key="header.key"
                  class="px-4 py-3 text-sm text-gray-900 max-w-xs truncate"
                  :title="String(row[header.key] || '')"
                >
                  {{ formatCellValue(row[header.key]) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- No Data -->
      <div v-else class="text-center py-8 text-gray-500">
        <p>No sample data available</p>
      </div>
    </div>

    <!-- No Preview Available -->
    <div v-else class="text-center py-8 text-gray-500">
      <svg class="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5h6m-6 4h6m2-7h.01M21 12h.01M21 16h.01M21 20h.01M21 24h.01" />
      </svg>
      <p class="mt-2">
        No preview available
      </p>
      <p class="text-sm">
        Select a dataset to view its contents
      </p>
    </div>
  </div>
</template>

<style scoped>
.dataset-preview {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
</style>
