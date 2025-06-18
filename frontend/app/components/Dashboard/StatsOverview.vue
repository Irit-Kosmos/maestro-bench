<script setup lang="ts">
import type { ExperimentStats } from '~/types'

interface Props {
  stats: ExperimentStats
  loading?: boolean
}

defineProps<Props>()
</script>

<template>
  <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
    <!-- Total Experiments -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <UIcon name="i-lucide:activity" class="h-8 w-8 text-blue-600" />
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">
              Total Experiments
            </dt>
            <dd class="text-2xl font-semibold text-gray-900">
              {{ loading ? '...' : stats.total }}
            </dd>
          </dl>
        </div>
      </div>
    </div>

    <!-- Completed -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <UIcon name="i-lucide:check-circle" class="h-8 w-8 text-green-600" />
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">
              Completed
            </dt>
            <dd class="text-2xl font-semibold text-gray-900">
              {{ loading ? '...' : stats.completed }}
            </dd>
          </dl>
        </div>
      </div>
    </div>

    <!-- Running -->
    <div class="bg-white rounded-lg shadow p-6">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <UIcon name="i-lucide:play-circle" class="h-8 w-8 text-blue-600" />
        </div>
        <div class="ml-5 w-0 flex-1">
          <dl>
            <dt class="text-sm font-medium text-gray-500 truncate">
              Running
            </dt>
            <dd class="text-2xl font-semibold text-gray-900">
              {{ loading ? '...' : stats.running }}
            </dd>
          </dl>
        </div>
      </div>
    </div>
  </div>
</template>
