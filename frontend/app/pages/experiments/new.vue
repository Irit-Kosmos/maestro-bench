<script setup lang="ts">
import type { CreateExperimentForm } from '~/types'

// Composables
const { datasets } = useDatasets()
const { createExperiment } = useExperiments()
const toast = useToast()
const { availableTeams } = useAgentTeams()

// Form state
const formData = ref<CreateExperimentForm>({
  name: '',
  dataset_id: undefined,
  agent_teams: [],
})

const isSubmitting = ref(false)

// Stepper configuration
const stepperItems = [
  {
    title: 'Experiment Name',
    description: 'Provide a name for your experiment',
    icon: 'i-lucide-file-text',
    slot: 'name',
  },
  {
    title: 'Dataset Selection',
    description: 'Choose the dataset for your experiment',
    icon: 'i-lucide-database',
    slot: 'dataset',
  },
  {
    title: 'Agent Teams',
    description: 'Select agent teams and configuration',
    icon: 'i-lucide-users',
    slot: 'teams',
  },
]

const currentStep = ref(0)
const stepper = useTemplateRef<any>('stepper')

// Computed
const formValid = computed(() => {
  return formData.value.name.trim() && formData.value.dataset_id != null
})

const isStepValid = computed(() => {
  switch (currentStep.value) {
    case 0:
      return formData.value.name.trim().length > 0
    case 1:
      return formData.value.dataset_id != null
    case 2:
      return true // Teams are optional
    default:
      return false
  }
})

const canGoNext = computed(() => {
  return isStepValid.value && stepper.value?.hasNext
})

// Computed property to handle dataset selection conversion between null and undefined
const selectedDataset = computed({
  get: () => formData.value.dataset_id ?? undefined,
  set: (value: number | undefined) => {
    formData.value.dataset_id = value ?? null
  },
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

function nextStep() {
  if (canGoNext.value) {
    stepper.value?.next()
  }
}

function prevStep() {
  if (stepper.value?.hasPrev) {
    stepper.value?.prev()
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
      toast.add({
        title: 'Success',
        description: 'Experiment created successfully!',
        color: 'success',
        icon: 'i-lucide:check-circle',
      })
      // Redirect to dashboard
      await navigateTo('/')
    }
    else {
      toast.add({
        title: 'Error',
        description: 'Failed to create experiment. Please try again.',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }
  catch (error) {
    console.error('Error creating experiment:', error)
    toast.add({
      title: 'Error',
      description: 'An unexpected error occurred. Please try again.',
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
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
    <div class="max-w-7xl mx-auto px-4 py-8">
      <!-- Experiment Configuration Form with Stepper -->
      <div class="bg-white rounded-lg shadow">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">
            Create New Experiment
          </h2>
          <p class="text-sm text-gray-600 mt-1">
            Follow the steps below to configure your experiment
          </p>
        </div>

        <div class="p-6">
          <!-- Stepper Component -->
          <UStepper
            ref="stepper"
            v-model="currentStep"
            :items="stepperItems"
            size="lg"
            class="w-full"
          >
            <!-- Step 1: Experiment Name -->
            <template #name>
              <div class="flex flex-col justify-center">
                <div class="max-w-md mx-auto w-full mt-6">
                  <label for="experiment-name" class="block text-sm font-medium text-gray-700 mb-2">
                    Experiment Name
                  </label>
                  <UInput
                    id="experiment-name"
                    v-model="formData.name"
                    size="lg"
                    placeholder="e.g., 'Corrector Agent Test v2.1'"
                    class="w-full"
                  />
                  <p class="text-xs text-gray-500 mt-2">
                    Use a clear, descriptive name for easy identification
                  </p>
                </div>
              </div>
            </template>

            <!-- Step 2: Dataset Selection -->
            <template #dataset>
              <div class="space-y-4  flex flex-col justify-center">
                <div class="max-w-md mx-auto mt-4 w-full">
                  <label for="dataset-select" class="block text-sm font-medium text-gray-700 mb-2">
                    Available Datasets
                  </label>
                  <USelect
                    id="dataset-select"
                    v-model="selectedDataset"
                    :items="datasets?.map(d => ({ label: `${d.name} - ${d.description}`, value: d.id })) || []"
                    value-key="value"
                    placeholder="Select a dataset..."
                    size="lg"
                    class="w-full"
                  />
                  <p class="text-xs text-gray-500 mt-2">
                    The dataset contains the questions/tasks for your experiment
                  </p>
                </div>
              </div>
            </template>

            <!-- Step 3: Agent Teams Selection -->
            <template #teams>
              <div class="space-y-6 ">
                <div v-if="availableTeams.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <UCard
                    v-for="team in availableTeams"
                    :key="team.id"
                    class="cursor-pointer hover:shadow-md transition-shadow"
                    :class="{
                      'ring-2 ring-primary-500 bg-primary-50': formData.agent_teams.includes(team.id.toString()),
                    }"
                    @click="() => toggleTeamSelection(team.id)"
                  >
                    <div class="flex items-start space-x-3">
                      <div class="flex-1 pointer-events-none">
                        <div class="block text-sm font-medium text-gray-900">
                          {{ team.name }}
                        </div>
                        <p class="text-sm text-gray-500 mt-1">
                          {{ team.description }}
                        </p>
                      </div>
                    </div>
                  </UCard>
                </div>

                <div v-else class="text-center py-8">
                  <UIcon name="i-lucide-users-x" class="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <h4 class="text-lg font-medium text-gray-900 mb-2">
                    No Agent Teams Available
                  </h4>
                  <p class="text-gray-600 mb-4">
                    You need to create agent teams before running experiments.
                  </p>
                  <UButton
                    to="/agents"
                    icon="i-lucide-plus"
                    variant="outline"
                  >
                    Create Agent Teams
                  </UButton>
                </div>

                <div class="bg-blue-50 rounded-lg p-4">
                  <div class="flex">
                    <UIcon name="i-lucide-info" class="h-5 w-5 text-blue-400 mt-0.5" />
                    <div class="ml-3">
                      <h4 class="text-sm font-medium text-blue-800">
                        Optional Step
                      </h4>
                      <p class="text-sm text-blue-700 mt-1">
                        You can create an experiment without selecting teams now and add them later.
                        Selected teams will run their agents against your chosen dataset.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </UStepper>

          <!-- Navigation Controls -->
          <div class="flex justify-between mt-8 pt-6 border-t border-gray-200">
            <div class="flex space-x-3">
              <UButton
                variant="outline"
                color="neutral"
                @click="handleCancel"
              >
                Cancel
              </UButton>
              <UButton
                v-if="stepper?.hasPrev"
                variant="outline"
                icon="i-lucide-arrow-left"
                @click="prevStep"
              >
                Previous
              </UButton>
            </div>

            <div class="flex space-x-3">
              <UButton
                v-if="stepper?.hasNext"
                :disabled="!isStepValid"
                trailing-icon="i-lucide-arrow-right"
                @click="nextStep"
              >
                Next
              </UButton>
              <UButton
                v-else
                :disabled="isSubmitting || !formValid"
                :loading="isSubmitting"
                icon="i-lucide-play"
                @click="handleSubmit"
              >
                Create & Launch Experiment
              </UButton>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
