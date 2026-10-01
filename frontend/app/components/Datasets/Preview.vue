<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import { h } from 'vue'

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
    cell: ({ row }) => {
      const value = formatCellValue(row.getValue(header.key))
      return h('span', { title: value }, value)
    },
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
  <div>
    <!-- Loading State -->
    <div v-if="loading" class="flex flex-col gap-3">
      <USkeleton class="h-4 w-56" />
      <USkeleton class="h-40 w-full" />
    </div>

    <!-- Error State -->
    <UAlert
      v-else-if="error"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-alert"
      title="Couldn’t load the preview"
      :description="String(error)"
      :actions="datasetId ? [{ label: 'Try again', color: 'error', variant: 'outline', onClick: () => { loadPreview(datasetId!) } }] : undefined"
    />

    <!-- Preview Content -->
    <div v-else-if="preview" class="flex flex-col gap-5">
      <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted tabular-nums">
        <UBadge
          :label="fileInfo?.type || 'Unknown'"
          :color="getFileTypeBadgeColor(fileInfo?.type || '')"
          variant="soft"
          size="sm"
        />
        <span><span class="font-medium text-highlighted">{{ (fileInfo?.rows || 0).toLocaleString('en-US') }}</span> rows</span>
        <span aria-hidden="true">·</span>
        <span><span class="font-medium text-highlighted">{{ fileInfo?.columns || 0 }}</span> columns</span>
      </p>

      <section aria-labelledby="columns-title">
        <h3 id="columns-title" class="text-xs font-medium text-muted mb-2">
          Columns
        </h3>
        <div class="flex flex-wrap gap-1.5">
          <UBadge
            v-for="header in displayHeaders"
            :key="header.key"
            :label="header.label"
            color="neutral"
            variant="outline"
            size="sm"
            class="font-mono"
          />
        </div>
      </section>

      <section v-if="sampleRows.length > 0" aria-labelledby="sample-title">
        <h3 id="sample-title" class="text-xs font-medium text-muted mb-2">
          First {{ sampleRows.length }} rows
        </h3>
        <div class="rounded-lg border border-default overflow-hidden">
          <UTable
            :data="sampleRows"
            :columns="tableColumns"
            :ui="{
              thead: 'bg-muted/60',
              th: 'px-3 py-2 text-xs font-medium text-muted font-mono',
              td: 'max-w-xs truncate px-3 py-2 text-sm text-toned',
            }"
            class="overflow-x-auto"
          />
        </div>
      </section>

      <p v-else class="text-sm text-muted">
        This file has no rows yet.
      </p>
    </div>
  </div>
</template>
