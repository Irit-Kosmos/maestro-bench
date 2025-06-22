<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'

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

// Computed property to create table columns from headers
const tableColumns = computed<TableColumn<any>[]>(() => {
  return displayHeaders.value.map(header => ({
    accessorKey: header.key,
    header: header.label,
    cell: ({ row }) => formatCellValue(row.getValue(header.key)),
  }))
})

// File type badge color mapping
function getFileTypeBadgeColor(fileType: string): 'success' | 'info' | 'warning' | 'neutral' {
  switch (fileType?.toLowerCase()) {
    case 'csv':
      return 'success'
    case 'json':
      return 'info'
    case 'xlsx':
    case 'xls':
      return 'warning'
    default:
      return 'neutral'
  }
}
</script>

<template>
  <div class="dataset-preview space-y-6">
    <!-- Loading State -->
    <UCard v-if="loading">
      <div class="flex items-center justify-center py-8">
        <USkeleton class="h-8 w-8 rounded-full" />
        <USkeleton class="ml-3 h-4 w-48" />
      </div>
    </UCard>

    <!-- Error State -->
    <UCard v-else-if="error" class="border-red-200 bg-red-50/50">
      <div class="flex items-center">
        <UIcon name="i-lucide-alert-circle" class="h-5 w-5 text-red-500" />
        <span class="ml-2 text-red-800 font-medium">Failed to load preview</span>
      </div>
      <p class="mt-2 text-red-700">
        {{ error }}
      </p>
    </UCard>

    <!-- Preview Content -->
    <div v-else-if="preview" class="space-y-6">
      <!-- File Info Card -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-file-text" class="h-5 w-5" />
            <h3 class="text-lg font-semibold">
              Dataset Information
            </h3>
          </div>
        </template>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="flex flex-col">
            <span class="text-sm font-medium text-neutral-600 mb-1">File Type</span>
            <UBadge
              :label="fileInfo?.type || 'Unknown'"
              :color="getFileTypeBadgeColor(fileInfo?.type || '')"
              variant="soft"
              class="w-fit"
            />
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-medium text-neutral-600 mb-1">Total Rows</span>
            <span class="text-lg font-semibold">{{ fileInfo?.rows || 0 }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-medium text-neutral-600 mb-1">Columns</span>
            <span class="text-lg font-semibold">{{ fileInfo?.columns || 0 }}</span>
          </div>
          <div class="flex flex-col">
            <span class="text-sm font-medium text-neutral-600 mb-1">Preview Sample</span>
            <span class="text-lg font-semibold">{{ sampleRows.length }} rows</span>
          </div>
        </div>
      </UCard>

      <!-- Column Headers Card -->
      <UCard>
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-columns" class="h-5 w-5" />
            <h4 class="text-lg font-semibold">
              Column Headers
            </h4>
            <UBadge :label="displayHeaders.length.toString()" color="neutral" variant="soft" />
          </div>
        </template>

        <div class="flex flex-wrap gap-2">
          <UBadge
            v-for="header in displayHeaders"
            :key="header.key"
            :label="header.label"
            color="primary"
            variant="subtle"
            class="text-xs"
          />
        </div>
      </UCard>

      <!-- Sample Data Table Card -->
      <UCard v-if="sampleRows.length > 0">
        <template #header>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-table" class="h-5 w-5" />
            <h4 class="text-lg font-semibold">
              Sample Data
            </h4>
            <UBadge
              :label="`First ${sampleRows.length} rows`"
              color="info"
              variant="soft"
            />
          </div>
        </template>

        <UTable
          :data="sampleRows"
          :columns="tableColumns"
          :ui="{
            td: 'max-w-xs truncate p-3',
            base: 'overflow-hidden',
          }"
          class="overflow-x-auto"
        />
      </UCard>

      <!-- No Sample Data Card -->
      <UCard v-else>
        <div class="text-center py-8">
          <UIcon name="i-lucide-database" class="mx-auto h-12 w-12 text-neutral-400 mb-4" />
          <p class="text-neutral-600">
            No sample data available
          </p>
        </div>
      </UCard>
    </div>

    <!-- No Preview Available -->
    <UCard v-else>
      <div class="text-center py-12">
        <UIcon name="i-lucide-file-search" class="mx-auto h-16 w-16 text-neutral-400 mb-4" />
        <h3 class="text-lg font-medium text-neutral-900 mb-2">
          No preview available
        </h3>
        <p class="text-neutral-600">
          Select a dataset to view its contents and structure
        </p>
      </div>
    </UCard>
  </div>
</template>
