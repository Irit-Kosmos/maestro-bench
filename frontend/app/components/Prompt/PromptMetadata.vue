<script setup lang="ts">
interface Props {
  createdAt?: string
  category?: string | null
  promptName?: string
  layout?: 'grid' | 'inline'
}

withDefaults(defineProps<Props>(), {
  layout: 'grid',
})

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString()
}
</script>

<template>
  <div class="border-t border-neutral-200 pt-4">
    <label class="block text-sm font-medium text-neutral-700 mb-3">
      Metadata
    </label>
    <div
      :class="[
        layout === 'grid' ? 'grid grid-cols-2 gap-4' : 'flex flex-wrap gap-4',
      ]"
      class="text-sm"
    >
      <div v-if="createdAt">
        <span class="text-neutral-500">Created:</span>
        <span class="ml-2 text-neutral-700">{{ formatDate(createdAt) }}</span>
      </div>
      <div v-if="category">
        <span class="text-neutral-500">Category:</span>
        <span class="ml-2 text-neutral-700">{{ category }}</span>
      </div>
      <div v-if="promptName">
        <span class="text-neutral-500">Prompt:</span>
        <span class="ml-2 text-neutral-700">{{ promptName }}</span>
      </div>
    </div>
  </div>
</template>
