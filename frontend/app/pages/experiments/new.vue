<script setup lang="ts">
import type { CreateExperimentForm } from '~/types'

// Composables
const { datasets } = useDatasets()
const { createExperiment } = useExperiments()
const toast = useToast()
const { agentTeams } = useAgentTeams()

// Get full teams data with agents
const fullTeams = computed(() => agentTeams.value || [])

// Form state
const formData = ref<CreateExperimentForm>({
  name: '',
  dataset_id: undefined,
  agent_teams: [],
})

const isSubmitting = ref(false)

// Enhanced state for agent team management
const selectedTeamId = ref<number | null>(null)
const agentConfigurations = ref<Record<number, {
  system_prompt?: string
  user_prompt?: string
  variables?: string
}>>({})

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
  return formData.value.name.trim()
    && formData.value.dataset_id != null
    && selectedTeamId.value != null
})

const isStepValid = computed(() => {
  switch (currentStep.value) {
    case 0:
      return formData.value.name.trim().length > 0
    case 1:
      return formData.value.dataset_id != null
    case 2:
      return selectedTeamId.value != null // Single team required
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

// Computed properties for enhanced agent management
const selectedTeam = computed(() => {
  return selectedTeamId.value ? fullTeams.value.find(team => team.id === selectedTeamId.value) : null
})

// Handlers
function selectTeam(teamId: number) {
  // Clear previous selection
  if (selectedTeamId.value !== null) {
    const previousTeam = fullTeams.value.find(t => t.id === selectedTeamId.value)
    if (previousTeam) {
      previousTeam.agents.forEach((agent) => {
        delete agentConfigurations.value[agent.id]
      })
    }
  }

  // Set new selection
  selectedTeamId.value = teamId
  formData.value.agent_teams = [teamId.toString()]

  // Initialize configurations for new team
  const team = fullTeams.value.find(t => t.id === teamId)
  if (team) {
    team.agents.forEach((agent) => {
      agentConfigurations.value[agent.id] = {
        system_prompt: agent.system_prompt || '',
        user_prompt: agent.user_prompt || '',
        variables: agent.variables || '',
      }
    })
  }
}

function updateAgentConfiguration(agentId: number, field: string, value: string) {
  if (!agentConfigurations.value[agentId]) {
    agentConfigurations.value[agentId] = {}
  }
  agentConfigurations.value[agentId][field as keyof typeof agentConfigurations.value[number]] = value
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
    // Prepare experiment data with agent configurations
    const experimentData = {
      name: formData.value.name.trim(),
      dataset_id: formData.value.dataset_id!,
      agent_teams: formData.value.agent_teams,
      agent_configurations: agentConfigurations.value,
    }

    const result = await createExperiment(experimentData)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Experiment created successfully with custom agent configurations!',
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
              <div class="space-y-6">
                <div class="max-w-2xl mx-auto w-full">
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

                <!-- Dataset Preview -->
                <div v-if="selectedDataset" class="max-w-4xl mx-auto w-full">
                  <DatasetsPreview :dataset-id="selectedDataset" />
                </div>
              </div>
            </template>

            <!-- Step 3: Agent Teams Selection -->
            <template #teams>
              <div class="space-y-6">
                <!-- Team Selection Grid -->
                <div v-if="fullTeams.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                  <UCard
                    v-for="team in fullTeams"
                    :key="team.id"
                    class="cursor-pointer hover:shadow-md transition-all duration-200"
                    :class="{
                      'ring-2 ring-primary-500 bg-primary-50': selectedTeamId === team.id,
                      'hover:ring-1 hover:ring-gray-300': selectedTeamId !== team.id,
                    }"
                    @click="selectTeam(team.id)"
                  >
                    <div class="flex items-start justify-between">
                      <div class="flex-1">
                        <div class="flex items-center justify-between mb-2">
                          <h4 class="text-lg font-medium text-gray-900">
                            {{ team.name }}
                          </h4>
                          <UBadge size="sm" variant="subtle" :color="selectedTeamId === team.id ? 'primary' : 'neutral'">
                            {{ team.agents.length }} agent{{ team.agents.length > 1 ? 's' : '' }}
                          </UBadge>
                        </div>
                        <p class="text-sm text-gray-500 mb-3">
                          {{ team.description }}
                        </p>
                        <div class="flex flex-wrap gap-2">
                          <UBadge
                            v-for="agent in team.agents"
                            :key="agent.id"
                            size="sm"
                            variant="outline"
                            :color="selectedTeamId === team.id ? 'primary' : 'neutral'"
                          >
                            {{ agent.name }}
                          </UBadge>
                        </div>
                      </div>
                    </div>
                  </UCard>
                </div>

                <!-- No Teams Available -->
                <div v-else class="text-center py-12">
                  <UIcon name="i-lucide-users-x" class="h-16 w-16 text-gray-400 mx-auto mb-4" />
                  <h4 class="text-lg font-medium text-gray-900 mb-2">
                    No Agent Teams Available
                  </h4>
                  <p class="text-gray-600 mb-6">
                    You need to create agent teams before running experiments.
                  </p>
                  <UButton
                    to="/agents"
                    icon="i-lucide-plus"
                    size="lg"
                  >
                    Create Agent Teams
                  </UButton>
                </div>

                <!-- Agent Configuration Section (appears when team is selected) -->
                <div v-if="selectedTeam" class="border-t border-gray-200 pt-8">
                  <div class="mb-6">
                    <h4 class="text-lg font-semibold text-gray-900 mb-2">
                      Configure {{ selectedTeam.name }} Agents
                    </h4>
                    <p class="text-gray-600">
                      Customize the configuration for each agent in your selected team
                    </p>
                  </div>

                  <!-- Agents Configuration Grid -->
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <UCard
                      v-for="agent in selectedTeam.agents"
                      :key="agent.id"
                      class="h-fit"
                    >
                      <template #header>
                        <div class="flex items-center justify-between">
                          <div class="mr-4">
                            <h5 class="text-base font-medium text-gray-900">
                              {{ agent.name }}
                            </h5>
                            <p v-if="agent.description" class="text-sm text-gray-500 mt-1 pr-4">
                              {{ agent.description }}
                            </p>
                          </div>
                          <UBadge variant="subtle" color="primary" class="min-w-16">
                            Agent {{ agent.id }}
                          </UBadge>
                        </div>
                      </template>

                      <div class="space-y-4">
                        <!-- System Prompt -->
                        <div>
                          <label class="block text-sm font-medium text-gray-700 mb-2">
                            System Prompt
                          </label>
                          <UTextarea
                            :model-value="agentConfigurations[agent.id]?.system_prompt || agent.system_prompt || ''"
                            placeholder="Enter system prompt..."
                            :rows="3"
                            resize
                            size="sm"
                            class="w-full"
                            @update:model-value="(value) => updateAgentConfiguration(agent.id, 'system_prompt', value)"
                          />
                        </div>

                        <!-- User Prompt -->
                        <div>
                          <label class="block text-sm font-medium text-gray-700 mb-2">
                            User Prompt
                          </label>
                          <UTextarea
                            :model-value="agentConfigurations[agent.id]?.user_prompt || agent.user_prompt || ''"
                            placeholder="Enter user prompt..."
                            :rows="5"
                            resize
                            size="sm"
                            class="w-full"
                            @update:model-value="(value) => updateAgentConfiguration(agent.id, 'user_prompt', value)"
                          />
                        </div>

                        <!-- Variables -->
                        <div>
                          <label class="block text-sm font-medium text-gray-700 mb-2">
                            Variables (JSON)
                          </label>
                          <UTextarea
                            :model-value="agentConfigurations[agent.id]?.variables || agent.variables || ''"
                            placeholder="{&quot;key&quot;: &quot;value&quot;}"
                            :rows="2"
                            resize
                            size="sm"
                            class="w-full"
                            @update:model-value="(value) => updateAgentConfiguration(agent.id, 'variables', value)"
                          />
                          <p class="text-xs text-gray-500 mt-1">
                            JSON format variables for agent execution
                          </p>
                        </div>

                        <!-- Reset Button -->
                        <div class="flex justify-end pt-2">
                          <UButton
                            variant="ghost"
                            size="xs"
                            icon="i-lucide-rotate-ccw"
                            @click="() => {
                              agentConfigurations[agent.id] = {
                                system_prompt: agent.system_prompt || '',
                                user_prompt: agent.user_prompt || '',
                                variables: agent.variables || '',
                              }
                            }"
                          >
                            Reset
                          </UButton>
                        </div>
                      </div>
                    </UCard>
                  </div>
                </div>

                <!-- Required Notice (only shown when no team selected) -->
                <div v-if="!selectedTeamId" class="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div class="flex">
                    <UIcon name="i-lucide-alert-triangle" class="h-5 w-5 text-amber-500 mt-0.5" />
                    <div class="ml-3">
                      <h4 class="text-sm font-medium text-amber-800">
                        Agent Team Required
                      </h4>
                      <p class="text-sm text-amber-700 mt-1">
                        You must select one agent team to proceed. The selected team will run its agents against your chosen dataset.
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
