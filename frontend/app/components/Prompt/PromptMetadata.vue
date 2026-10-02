<script setup lang="ts">
interface Props {
  createdAt?: string
  promptName?: string
  layout?: 'grid' | 'inline'
}

withDefaults(defineProps<Props>(), {
  layout: 'grid',
})

const { formatDate } = useUIHelpers()
</script>

<template>
  <div class="border-t border-default pt-4">
    <label class="block text-sm font-medium text-default mb-3">
      Metadata
    </label>
    <div
      :class="[
        layout === 'grid' ? 'grid grid-cols-2 gap-4' : 'flex flex-wrap gap-4',
      ]"
      class="text-sm"
    >
      <div v-if="createdAt">
        <span class="text-muted">Created:</span>
        <span class="ml-2 text-default">{{ formatDate(createdAt) }}</span>
      </div>
      <div v-if="promptName">
        <span class="text-muted">Prompt:</span>
        <span class="ml-2 text-default">{{ promptName }}</span>
      </div>
    </div>
  </div>
</template>
