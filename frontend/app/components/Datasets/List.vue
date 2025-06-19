<script setup lang="ts">
import type { Dataset } from '~/types'

interface Props {
  datasets: readonly Dataset[] | null
  loading?: boolean
}

interface Emits {
  refresh: []
  view: [id: number]
  delete: [id: number]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const { formatDate } = useUIHelpers()

function handleRefresh() {
  emit('refresh')
}

function handleView(id: number) {
  emit('view', id)
}

function handleDelete(id: number) {
  emit('delete', id)
}
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex justify-between items-center">
        <h2 class="text-lg font-semibold text-gray-900">
          Available Datasets
        </h2>
        <UButton
          variant="ghost"
          size="sm"
          icon="i-lucide:refresh-cw"
          :loading="loading"
          @click="handleRefresh"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <div class="overflow-hidden">
      <!-- Empty State -->
      <div v-if="!datasets || datasets.length === 0" class="p-12 text-center">
        <UIcon name="i-lucide:database" class="mx-auto h-12 w-12 text-gray-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          No datasets yet
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          Get started by creating your first dataset.
        </p>
      </div>

      <!-- Datasets Grid -->
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 p-6">
        <UCard
          v-for="dataset in datasets"
          :key="dataset.id"
          class="hover:shadow-md transition-shadow"
        >
          <div class="space-y-3">
            <div class="flex justify-between items-start">
              <h3 class="text-lg font-semibold text-gray-900">
                {{ dataset.name }}
              </h3>
              <UBadge color="info" variant="soft">
                ID: {{ dataset.id }}
              </UBadge>
            </div>

            <p class="text-gray-600 text-sm">
              {{ dataset.description }}
            </p>

            <div class="flex justify-between items-center pt-3 border-t border-gray-100">
              <span class="text-xs text-gray-500">
                Created: {{ formatDate(dataset.created_at) }}
              </span>
              <div class="flex space-x-2">
                <UButton
                  variant="ghost"
                  size="sm"
                  icon="i-lucide:eye"
                  @click="() => handleView(dataset.id)"
                >
                  View
                </UButton>
              </div>
            </div>
          </div>
        </UCard>
      </div>
    </div>
  </div>
</template>
