<script setup lang="ts">
import type { Experiment } from '~/types'

interface Props {
  experiments: Experiment[] | null
  loading?: boolean
}

interface Emits {
  refresh: []
  viewExperiment: [id: number]
  deleteExperiment: [id: number]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const { getStatusColor, formatDate } = useUIHelpers()

function handleViewExperiment(id: number) {
  emit('viewExperiment', id)
}

function handleDeleteExperiment(id: number) {
  emit('deleteExperiment', id)
}

function handleRefresh() {
  emit('refresh')
}

async function handleCreateNew() {
  await navigateTo('/experiments/new')
}
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">
            Recent Experiments
          </h2>
        </div>
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
      <div v-if="!experiments || experiments.length === 0" class="p-12 text-center">
        <UIcon name="i-lucide:flask" class="mx-auto h-12 w-12 text-gray-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          No experiments yet
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          Get started by creating your first experiment.
        </p>
        <div class="mt-6">
          <UButton
            variant="solid"
            color="primary"
            icon="i-lucide:plus"
            @click="handleCreateNew"
          >
            Create Experiment
          </UButton>
        </div>
      </div>

      <!-- Experiments Table -->
      <div v-else class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Experiment
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Dataset
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Results
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="experiment in experiments" :key="experiment.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div>
                  <div class="text-sm font-medium text-gray-900">
                    {{ experiment.name }}
                  </div>
                  <div class="text-sm text-gray-500">
                    ID: {{ experiment.id }}
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="text-sm text-gray-900">
                  {{ experiment.dataset?.name || 'Unknown' }}
                </div>
                <div class="text-sm text-gray-500">
                  {{ experiment.dataset?.description }}
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <UBadge
                  :color="getStatusColor(experiment.status || 'pending')"
                  variant="soft"
                >
                  {{ experiment.status || 'pending' }}
                </UBadge>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                <div v-if="experiment.results">
                  <div v-if="experiment.results.total_questions" class="text-gray-500">
                    {{ experiment.results.total_questions }} questions
                  </div>
                </div>
                <span v-else class="text-gray-400">No results yet</span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ formatDate(experiment.created_at) }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <div class="flex space-x-2">
                  <UButton
                    variant="ghost"
                    size="sm"
                    icon="i-lucide:eye"
                    @click="() => handleViewExperiment(experiment.id)"
                  >
                    View
                  </UButton>
                  <UButton
                    variant="ghost"
                    size="sm"
                    color="error"
                    icon="i-lucide:trash-2"
                    @click="() => handleDeleteExperiment(experiment.id)"
                  >
                    Delete
                  </UButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
