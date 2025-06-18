<script setup lang="ts">
import type { CreateExperimentForm } from '~/types'

// Composables
const { datasets } = useDatasets()
const { createExperiment } = useExperiments()
const { showSuccess, showError } = useNotifications()
const { availableTeams } = useAgentTeams()

// Form state
const formData = ref<CreateExperimentForm>({
  name: '',
  dataset_id: null,
  agent_teams: [],
})

const isSubmitting = ref(false)

// Computed
const formValid = computed(() => {
  return formData.value.name.trim() && formData.value.dataset_id !== null
})

// Handlers
function toggleTeamSelection(teamId: number) {
  const teamIdStr = teamId.toString()
  const teams = formData.value.agent_teams
  const index = teams.indexOf(teamIdStr)

  if (index > -1) {
    // Remove team if already selected
    teams.splice(index, 1)
  }
  else {
    // Add team if not selected
    teams.push(teamIdStr)
  }
}

async function handleSubmit() {
  if (!formValid.value)
    return

  isSubmitting.value = true

  try {
    const result = await createExperiment({
      name: formData.value.name.trim(),
      dataset_id: formData.value.dataset_id!,
    })

    if (result.success) {
      showSuccess('Experiment created successfully!')
      // Redirect to dashboard
      await navigateTo('/')
    }
    else {
      showError('Failed to create experiment. Please try again.')
    }
  }
  catch (error) {
    console.error('Error creating experiment:', error)
    showError('An unexpected error occurred. Please try again.')
  }
  finally {
    isSubmitting.value = false
  }
}

async function handleCancel() {
  await navigateTo('/')
}
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Experiment Configuration Form -->
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">
            Experiment Configuration
          </h2>
        </div>

        <form class="p-6 space-y-6" @submit.prevent="handleSubmit">
          <!-- Basic Information -->
          <div class="space-y-4">
            <h3 class="text-md font-medium text-gray-900">
              Basic Information
            </h3>

            <div>
              <label for="name" class="block text-sm font-medium text-gray-700 mb-1">
                Experiment Name
              </label>
              <input
                id="name"
                v-model="formData.name"
                type="text"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter experiment name (e.g., 'Corrector Agent Test v2.1')"
              >
            </div>

            <div>
              <label for="dataset" class="block text-sm font-medium text-gray-700 mb-1">
                Dataset
              </label>
              <select
                id="dataset"
                v-model="formData.dataset_id"
                required
                class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">
                  Select a dataset...
                </option>
                <option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
                  {{ dataset.name }} - {{ dataset.description }}
                </option>
              </select>
            </div>
          </div>

          <!-- Agent Team Selection -->
          <div class="space-y-4">
            <h3 class="text-md font-medium text-gray-900">
              Agent Teams
            </h3>
            <p class="text-sm text-gray-600">
              Select which agent teams to include in this experiment
            </p>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <UCard
                v-for="team in availableTeams"
                :key="team.id"
                class="cursor-pointer hover:shadow-md transition-shadow"
                @click="() => toggleTeamSelection(team.id)"
              >
                <div class="flex items-start space-x-3">
                  <input
                    :id="`team-${team.id}`"
                    v-model="formData.agent_teams"
                    type="checkbox"
                    :value="team.id.toString()"
                    class="mt-1 h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded pointer-events-none"
                  >
                  <div class="flex-1 pointer-events-none">
                    <div class="block text-sm font-medium text-gray-900">
                      {{ team.name }}
                    </div>
                    <p class="text-sm text-gray-500">
                      {{ team.description }}
                    </p>
                  </div>
                </div>
              </UCard>
            </div>
          </div>

          <!-- Advanced Configuration (Placeholder) -->
          <div class="space-y-4">
            <h3 class="text-md font-medium text-gray-900">
              Advanced Configuration
            </h3>
            <div class="bg-yellow-50 rounded-lg p-4">
              <div class="flex">
                <UIcon name="i-lucide:info" class="h-5 w-5 text-yellow-400" />
                <div class="ml-3">
                  <h4 class="text-sm font-medium text-yellow-800">
                    Coming Soon
                  </h4>
                  <p class="text-sm text-yellow-700 mt-1">
                    Advanced configuration options like prompt customization, sampling parameters,
                    and evaluation metrics will be available in future versions.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Submit Button -->
          <div class="flex justify-end pt-6 border-t border-gray-200">
            <div class="flex space-x-3">
              <UButton
                type="button"
                variant="outline"
                color="neutral"
                @click="handleCancel"
              >
                Cancel
              </UButton>
              <UButton
                type="submit"
                variant="solid"
                color="primary"
                :disabled="isSubmitting || !formValid"
                :loading="isSubmitting"
                icon="i-lucide:play"
              >
                Create & Launch Experiment
              </UButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
