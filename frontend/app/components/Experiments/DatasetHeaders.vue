<script setup lang="ts">
interface Props {
  datasetId: number
}

const props = defineProps<Props>()

const { preview, loadPreview, loading, error } = useDatasetPreview()

// Load preview when component mounts or datasetId changes
watch(
  () => props.datasetId,
  (newId) => {
    if (newId) {
      loadPreview(newId)
    }
  },
  { immediate: true },
)
</script>

<template>
  <div>
    <div v-if="loading" class="flex items-center justify-center py-4">
      <UIcon name="i-lucide-loader-2" class="w-4 h-4 animate-spin text-neutral-500" />
      <span class="ml-2 text-sm text-neutral-500">Loading dataset headers...</span>
    </div>

    <div v-else-if="error" class="p-3 bg-red-50 rounded-md">
      <div class="flex items-center">
        <UIcon name="i-lucide-alert-circle" class="w-4 h-4 text-red-500" />
        <span class="ml-2 text-sm text-red-700">{{ error }}</span>
      </div>
    </div>

    <div v-else-if="preview" class="space-y-2">
      <div class="flex flex-wrap gap-2">
        <UBadge
          v-for="header in preview.headers"
          :key="header"
          variant="outline"
          color="neutral"
          size="sm"
        >
          {{ header }}
        </UBadge>
      </div>
      <div class="text-xs text-neutral-500">
        {{ preview.total_columns }} columns
      </div>
    </div>

    <div v-else class="text-sm text-neutral-500">
      No dataset headers available
    </div>
  </div>
</template>
