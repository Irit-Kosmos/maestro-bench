<script setup lang="ts">
interface Props {
  datasetInfo: any
}

defineProps<Props>()
</script>

<template>
  <UCard v-if="datasetInfo">
    <template #header>
      <div class="flex items-center gap-3">
        <UIcon name="i-lucide-database" class="h-6 w-6" />
        <h2 class="text-xl font-semibold text-neutral-900">
          Dataset Configuration
        </h2>
      </div>
    </template>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Name
        </dt>
        <dd class="text-sm text-neutral-900">
          {{ datasetInfo.name }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          File Path
        </dt>
        <dd class="text-sm text-neutral-900 font-mono">
          {{ datasetInfo.file_path }}
        </dd>
      </div>
      <div>
        <dt class="text-sm font-medium text-neutral-500 mb-2">
          Description
        </dt>
        <dd class="text-sm text-neutral-900">
          {{ datasetInfo.description || 'No description' }}
        </dd>
      </div>
    </div>
  </UCard>
</template>
