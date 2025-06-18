<script setup lang="ts">
interface QuickAction {
  title: string
  description: string
  icon: string
  color: string
  route: string
}

const actions: QuickAction[] = [
  {
    title: 'Run New Experiment',
    description: 'Configure and launch a new benchmark test',
    icon: 'i-lucide:flask-conical',
    color: 'text-blue-600',
    route: '/experiments/new',
  },
  {
    title: 'Manage Datasets',
    description: 'Upload and organize your benchmark datasets',
    icon: 'i-lucide:database',
    color: 'text-green-600',
    route: '/datasets',
  },
  {
    title: 'Agent Configuration',
    description: 'Configure prompts and agent team settings',
    icon: 'i-lucide:users',
    color: 'text-purple-600',
    route: '/agents',
  },
]

async function handleActionClick(route: string) {
  await navigateTo(route)
}
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <h2 class="text-lg font-semibold text-gray-900">
        Quick Actions
      </h2>
    </div>
    <div class="p-6">
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <UCard
          v-for="action in actions"
          :key="action.route"
          class="hover:shadow-md transition-shadow cursor-pointer"
          @click="() => handleActionClick(action.route)"
        >
          <div class="flex items-center space-x-4">
            <div class="flex-shrink-0">
              <UIcon :name="action.icon" :class="`h-8 w-8 ${action.color}`" />
            </div>
            <div>
              <h3 class="text-lg font-medium text-gray-900">
                {{ action.title }}
              </h3>
              <p class="text-sm text-gray-500">
                {{ action.description }}
              </p>
            </div>
          </div>
        </UCard>
      </div>
    </div>
  </div>
</template>
