<script setup lang="ts">
import type { CreateExperimentForm } from '~/types'

// Composables
const { datasets } = useDatasets()
const { createExperiment } = useExperiments()
const { agentTeams } = useAgentTeams()
const { allPromptVersions } = usePrompts()
const { models } = useModels()
const toast = useToast()

// Get full teams data with agents
const fullTeams = computed(() => agentTeams.value || [])

// Form state - updated for new backend architecture
const formData = ref<CreateExperimentForm>({
  name: '',
  dataset_id: undefined,
  agent_teams: [],
})

const isSubmitting = ref(false)

// Enhanced state for agent configuration with new architecture
const selectedTeamId = ref<number | null>(null)
const agentConfigurations = ref<Record<number, {
  prompt_version_id?: number
  model_id?: number
  temperature?: number
  max_tokens?: number
  is_active?: boolean
}>>({})

// Modal state for prompt details
const showPromptDetailsModal = ref(false)
const selectedPromptVersionForDetails = ref<any>(null)

// Stepper configuration
const stepperItems = [
  {
    title: 'Experiment Details',
    description: 'Provide experiment name and description',
    icon: 'i-lucide-file-text',
    slot: 'details',
  },
  {
    title: 'Dataset Selection',
    description: 'Choose the dataset for your experiment',
    icon: 'i-lucide-database',
    slot: 'dataset',
  },
  {
    title: 'Dataset Sampling',
    description: 'Configure which data rows to use',
    icon: 'i-lucide-filter',
    slot: 'sampling',
  },
  {
    title: 'Agent Team & Configuration',
    description: 'Select team and configure agents',
    icon: 'i-lucide-users',
    slot: 'agents',
  },
]

const currentStep = ref(0)
const stepper = useTemplateRef<any>('stepper')

// Form data for experiment details
const experimentDetails = ref({
  name: '',
  description: '',
})

// Dataset sampling configuration
const samplingConfig = ref({
  sampling_type: 'all',
  sampling_size: undefined as number | undefined,
  sampling_start_row: undefined as number | undefined,
  sampling_end_row: undefined as number | undefined,
})

// Computed
const isStepValid = computed(() => {
  switch (currentStep.value) {
    case 0:
      return experimentDetails.value.name.trim().length > 0
    case 1:
      return formData.value.dataset_id != null
    case 2:
      // Sampling step validation
      if (samplingConfig.value.sampling_type === 'random') {
        return samplingConfig.value.sampling_size && samplingConfig.value.sampling_size > 0
      }
      if (samplingConfig.value.sampling_type === 'range') {
        return samplingConfig.value.sampling_start_row
          && samplingConfig.value.sampling_end_row
          && samplingConfig.value.sampling_start_row <= samplingConfig.value.sampling_end_row
      }
      return true // 'all' option is always valid
    case 3:
      return selectedTeamId.value != null
    default:
      return false
  }
})

const formValid = computed(() => {
  return experimentDetails.value.name.trim()
    && formData.value.dataset_id != null
    && selectedTeamId.value != null
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

// Get available prompt versions for dropdowns
const promptVersionOptions = computed(() => {
  const options: Array<{ label: string, value: number }> = []

  allPromptVersions.value?.forEach((version) => {
    if (version.is_active) {
      options.push({
        label: `${version.prompt?.name || 'Unknown'} v${version.version}${version.is_default ? ' (Default)' : ''}`,
        value: version.id,
      })
    }
  })

  return options
})

const modelOptions = computed(() => {
  return models.value?.filter(model => model.is_active).map(model => ({
    label: `${model.name} (${model.provider})`,
    value: model.id,
  })) || []
})

// Page meta
useSeoMeta({
  title: 'Create New Experiment',
  description: 'Configure and launch a new MAESTRO experiment',
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

  // Initialize configurations for new team with default values
  const team = fullTeams.value.find(t => t.id === teamId)
  if (team) {
    team.agents.forEach((agent) => {
      agentConfigurations.value[agent.id] = {
        prompt_version_id: agent.default_prompt_version_id || undefined,
        model_id: agent.default_model_id || undefined,
        temperature: undefined, // Will use model default
        max_tokens: undefined, // Will use model default
        is_active: true,
      }
    })
  }
}

function updateAgentConfiguration(agentId: number, field: string, value: any) {
  if (!agentConfigurations.value[agentId]) {
    agentConfigurations.value[agentId] = {}
  }
  agentConfigurations.value[agentId][field as keyof typeof agentConfigurations.value[number]] = value
}

function openPromptDetails(promptVersionId: number) {
  const promptVersion = allPromptVersions.value?.find(v => v.id === promptVersionId)
  if (promptVersion) {
    selectedPromptVersionForDetails.value = promptVersion
    showPromptDetailsModal.value = true
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
    // Prepare experiment data with new architecture
    const experimentData = {
      name: experimentDetails.value.name.trim(),
      description: experimentDetails.value.description.trim() || undefined,
      dataset_id: formData.value.dataset_id!,
      agent_teams: formData.value.agent_teams,
      agent_configurations: agentConfigurations.value,
      sampling_type: samplingConfig.value.sampling_type,
      sampling_size: samplingConfig.value.sampling_size,
      sampling_start_row: samplingConfig.value.sampling_start_row,
      sampling_end_row: samplingConfig.value.sampling_end_row,
    }

    const result = await createExperiment(experimentData)

    if (result.success) {
      toast.add({
        title: 'Success',
        description: 'Experiment created successfully with modern configuration!',
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
        <div class="px-6 py-4 border-b border-neutral-200">
          <h2 class="text-lg font-semibold text-neutral-900">
            Create New Experiment
          </h2>
          <p class="text-sm text-neutral-600 mt-1">
            Configure your experiment with prompt version and model selection
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
            <!-- Step 1: Experiment Details -->
            <template #details>
              <div class="flex flex-col justify-center">
                <div class="max-w-md mx-auto w-full mt-6">
                  <div class="space-y-4">
                    <UFormField label="Experiment Name" required>
                      <UInput
                        v-model="experimentDetails.name"
                        size="lg"
                        placeholder="e.g., 'Corrector Agent Test v2.1'"
                        class="w-full"
                      />
                    </UFormField>

                    <UFormField label="Description">
                      <UTextarea
                        v-model="experimentDetails.description"
                        placeholder="Optional description of this experiment"
                        :rows="3"
                        class="w-full"
                      />
                    </UFormField>
                  </div>
                  <p class="text-xs text-neutral-500 mt-4">
                    Use a clear, descriptive name for easy identification
                  </p>
                </div>
              </div>
            </template>

            <!-- Step 2: Dataset Selection -->
            <template #dataset>
              <div class="space-y-6">
                <div class="max-w-2xl mx-auto w-full">
                  <UFormField label="Available Datasets" required>
                    <USelect
                      v-model="selectedDataset"
                      :items="datasets?.map(d => ({ label: `${d.name} - ${d.description}`, value: d.id })) || []"
                      placeholder="Select a dataset..."
                      size="lg"
                      class="w-full"
                    />
                  </UFormField>
                  <p class="text-xs text-neutral-500 mt-2">
                    The dataset contains the questions/tasks for your experiment
                  </p>
                </div>

                <!-- Dataset Preview - Collapsible -->
                <div v-if="selectedDataset" class="max-w-4xl mx-auto w-full">
                  <UCollapsible :default-open="false" class="flex flex-col gap-4">
                    <UButton
                      label="Dataset Preview"
                      color="neutral"
                      variant="subtle"
                      leading-icon="i-lucide-eye"
                      trailing-icon="i-lucide-chevron-down"
                      class="group"
                      :ui="{
                        trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
                      }"
                      block
                    />

                    <template #content>
                      <div class="p-1">
                        <DatasetsPreview :dataset-id="selectedDataset" />
                      </div>
                    </template>
                  </UCollapsible>
                </div>
              </div>
            </template>

            <!-- Step 3: Dataset Sampling Configuration -->
            <template #sampling>
              <div class="space-y-6">
                <ExperimentsDatasetSamplingConfig
                  v-if="selectedDataset"
                  :dataset-id="selectedDataset"
                  :sampling-type="samplingConfig.sampling_type"
                  :sampling-size="samplingConfig.sampling_size"
                  :sampling-start-row="samplingConfig.sampling_start_row"
                  :sampling-end-row="samplingConfig.sampling_end_row"
                  @update:sampling-type="(value: string) => samplingConfig.sampling_type = value"
                  @update:sampling-size="(value: number | undefined) => samplingConfig.sampling_size = value"
                  @update:sampling-start-row="(value: number | undefined) => samplingConfig.sampling_start_row = value"
                  @update:sampling-end-row="(value: number | undefined) => samplingConfig.sampling_end_row = value"
                />

                <div v-else class="text-center py-12">
                  <UIcon name="i-lucide-arrow-left" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
                  <h3 class="text-lg font-medium text-neutral-900 mb-2">
                    Select a Dataset First
                  </h3>
                  <p class="text-neutral-600">
                    Go back to the previous step to choose a dataset before configuring sampling options.
                  </p>
                </div>
              </div>
            </template>

            <!-- Step 4: Agent Team & Configuration -->
            <template #agents>
              <div class="space-y-6">
                <!-- Team Selection Grid -->
                <div v-if="fullTeams.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
                  <UCard
                    v-for="team in fullTeams"
                    :key="team.id"
                    class="cursor-pointer hover:shadow-md transition-all duration-200"
                    :class="{
                      'ring-2 ring-primary-500 bg-primary-50': selectedTeamId === team.id,
                      'hover:ring-1 hover:ring-neutral-300': selectedTeamId !== team.id,
                    }"
                    @click="selectTeam(team.id)"
                  >
                    <div class="flex items-start justify-between">
                      <div class="flex-1">
                        <div class="flex items-center justify-between mb-2">
                          <h4 class="text-lg font-medium text-neutral-900">
                            {{ team.name }}
                          </h4>
                          <UBadge size="sm" variant="subtle" :color="selectedTeamId === team.id ? 'primary' : 'neutral'">
                            {{ team.agents.length }} agent{{ team.agents.length > 1 ? 's' : '' }}
                          </UBadge>
                        </div>
                        <p class="text-sm text-neutral-500 mb-3">
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
                  <UIcon name="i-lucide-users-x" class="h-16 w-16 text-neutral-400 mx-auto mb-4" />
                  <h4 class="text-lg font-medium text-neutral-900 mb-2">
                    No Agent Teams Available
                  </h4>
                  <p class="text-neutral-600 mb-6">
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
                <div v-if="selectedTeam" class="border-t border-neutral-200 pt-8">
                  <div class="mb-6">
                    <h4 class="text-lg font-semibold text-neutral-900 mb-2">
                      Configure {{ selectedTeam.name }} Agents
                    </h4>
                    <p class="text-neutral-600">
                      Select prompt versions and models for each agent, or use their defaults
                    </p>
                  </div>

                  <!-- Agents Configuration Grid -->
                  <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <UCard
                      v-for="agent in selectedTeam.agents"
                      :key="agent.id"
                      class="h-fit"
                      :class="{
                        'ring-2 ring-primary-500 bg-primary-50': agentConfigurations[agent.id]?.is_active,
                        'hover:ring-1 hover:ring-neutral-300 opacity-70': !agentConfigurations[agent.id]?.is_active,
                      }"
                    >
                      <template #header>
                        <div class="flex items-center justify-between">
                          <div class="mr-4">
                            <h5 class="text-base font-medium text-neutral-900">
                              {{ agent.name }}
                            </h5>
                            <p v-if="agent.description" class="text-sm text-neutral-500 mt-1 pr-4">
                              {{ agent.description }}
                            </p>
                          </div>
                          <USwitch
                            :model-value="agentConfigurations[agent.id]?.is_active ?? true"
                            @update:model-value="(value: boolean) => updateAgentConfiguration(agent.id, 'is_active', value)"
                          />
                        </div>
                      </template>

                      <div class="space-y-4">
                        <!-- Prompt Version Selection -->
                        <UFormField label="Prompt Version">
                          <USelect
                            :model-value="agentConfigurations[agent.id]?.prompt_version_id"
                            :items="promptVersionOptions"
                            placeholder="Select prompt version..."
                            class="w-full"
                            @update:model-value="(value) => updateAgentConfiguration(agent.id, 'prompt_version_id', value)"
                          />
                          <div v-if="agentConfigurations[agent.id]?.prompt_version_id" class="mt-2 flex justify-end">
                            <UButton
                              variant="ghost"
                              size="xs"
                              icon="i-lucide-eye"
                              @click="openPromptDetails(agentConfigurations[agent.id]?.prompt_version_id!)"
                            >
                              See details
                            </UButton>
                          </div>
                        </UFormField>

                        <!-- Model Selection -->
                        <UFormField label="Model">
                          <USelect
                            :model-value="agentConfigurations[agent.id]?.model_id"
                            :items="modelOptions"
                            placeholder="Select model..."
                            class="w-full"
                            @update:model-value="(value) => updateAgentConfiguration(agent.id, 'model_id', value)"
                          />
                        </UFormField>

                        <!-- Advanced Configuration -->
                        <div class="grid grid-cols-2 gap-3">
                          <UFormField label="Temperature">
                            <UInput
                              :model-value="agentConfigurations[agent.id]?.temperature?.toString() || ''"
                              type="number"
                              step="0.1"
                              min="0"
                              max="1"
                              placeholder="0"
                              @update:model-value="(value: string) => updateAgentConfiguration(agent.id, 'temperature', value ? Number.parseFloat(value) : undefined)"
                            />
                          </UFormField>

                          <UFormField label="Max Tokens">
                            <UInput
                              :model-value="agentConfigurations[agent.id]?.max_tokens?.toString() || ''"
                              type="number"
                              min="100"
                              placeholder="10000"
                              @update:model-value="(value: string) => updateAgentConfiguration(agent.id, 'max_tokens', value ? Number.parseInt(value) : undefined)"
                            />
                          </UFormField>
                        </div>
                        <!-- Reset to Defaults Button -->
                        <div class="flex justify-end pt-2">
                          <UButton
                            variant="ghost"
                            size="xs"
                            icon="i-lucide-rotate-ccw"
                            @click="() => {
                              agentConfigurations[agent.id] = {
                                prompt_version_id: agent.default_prompt_version_id || undefined,
                                model_id: agent.default_model_id || undefined,
                                temperature: undefined,
                                max_tokens: undefined,
                                is_active: true,
                              }
                            }"
                          >
                            Reset to Defaults
                          </UButton>
                        </div>
                      </div>
                    </UCard>
                  </div>
                </div>
              </div>
            </template>
          </UStepper>
        </div>

        <!-- Footer Actions -->
        <div class="px-6 py-4 border-t border-neutral-200 bg-neutral-50">
          <div class="flex justify-between">
            <div class="flex space-x-3">
              <UButton
                variant="ghost"
                @click="handleCancel"
              >
                Cancel
              </UButton>
              <UButton
                v-if="stepper?.hasPrev"
                variant="outline"
                icon="i-lucide-chevron-left"
                @click="prevStep"
              >
                Previous
              </UButton>
            </div>

            <div class="flex space-x-3">
              <UButton
                v-if="stepper?.hasNext"
                variant="solid"
                icon-trailing="i-lucide-chevron-right"
                :disabled="!isStepValid"
                @click="nextStep"
              >
                Next
              </UButton>
              <UButton
                v-else
                variant="solid"
                color="primary"
                icon="i-lucide-play"
                :disabled="!formValid"
                :loading="isSubmitting"
                @click="handleSubmit"
              >
                Create & Start Experiment
              </UButton>
            </div>
          </div>
        </div>
      </div>

      <!-- Prompt Details Modal -->
      <UModal v-model:open="showPromptDetailsModal">
        <template #content>
          <UCard class="overflow-auto max-h-[80vh]">
            <template #header>
              <div class="flex items-center justify-between">
                <h3 class="text-base font-semibold leading-6 text-neutral-900 dark:text-white">
                  Prompt Details: {{ selectedPromptVersionForDetails?.prompt?.name }} v{{ selectedPromptVersionForDetails?.version }}
                </h3>
                <UButton color="neutral" variant="ghost" icon="i-lucide-x" class="-my-1" @click="showPromptDetailsModal = false" />
              </div>
            </template>

            <div v-if="selectedPromptVersionForDetails" class="space-y-6">
              <!-- Basic Info -->
              <div class="grid grid-cols-2 gap-4">
                <div>
                  <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                    Prompt Name
                  </h4>
                  <p class="text-sm text-neutral-600 dark:text-neutral-300">
                    {{ selectedPromptVersionForDetails.prompt?.name || 'Unknown' }}
                  </p>
                </div>
                <div>
                  <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                    Version
                  </h4>
                  <div class="flex items-center gap-2">
                    <UBadge size="sm" variant="subtle">
                      v{{ selectedPromptVersionForDetails.version }}
                    </UBadge>
                    <UBadge v-if="selectedPromptVersionForDetails.is_default" size="sm" color="success">
                      Default
                    </UBadge>
                  </div>
                </div>
              </div>

              <!-- Description -->
              <div v-if="selectedPromptVersionForDetails.prompt?.description">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  Description
                </h4>
                <p class="text-sm text-neutral-600 dark:text-neutral-300">
                  {{ selectedPromptVersionForDetails.prompt.description }}
                </p>
              </div>

              <!-- System Prompt -->
              <div v-if="selectedPromptVersionForDetails.system_prompt">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  System Prompt
                </h4>
                <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
                  <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ selectedPromptVersionForDetails.system_prompt }}</pre>
                </div>
              </div>

              <!-- User Prompt -->
              <div v-if="selectedPromptVersionForDetails.user_prompt">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  User Prompt
                </h4>
                <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
                  <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ selectedPromptVersionForDetails.user_prompt }}</pre>
                </div>
              </div>

              <!-- Variables -->
              <div v-if="selectedPromptVersionForDetails.variables">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  Variables
                </h4>
                <div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg p-4">
                  <pre class="text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">{{ selectedPromptVersionForDetails.variables }}</pre>
                </div>
              </div>

              <!-- Notes -->
              <div v-if="selectedPromptVersionForDetails.notes">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  Notes
                </h4>
                <p class="text-sm text-neutral-600 dark:text-neutral-300">
                  {{ selectedPromptVersionForDetails.notes }}
                </p>
              </div>

              <!-- Metadata -->
              <div class="border-t pt-4">
                <h4 class="text-sm font-medium text-neutral-900 dark:text-white mb-2">
                  Metadata
                </h4>
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="text-neutral-500 dark:text-neutral-400">Created:</span>
                    <span class="ml-2 text-neutral-700 dark:text-neutral-300">{{ new Date(selectedPromptVersionForDetails.created_at).toLocaleDateString() }}</span>
                  </div>
                  <div>
                    <span class="text-neutral-500 dark:text-neutral-400">Category:</span>
                    <span class="ml-2 text-neutral-700 dark:text-neutral-300">{{ selectedPromptVersionForDetails.prompt?.category || 'Uncategorized' }}</span>
                  </div>
                </div>
              </div>
            </div>

            <template #footer>
              <div class="flex justify-end">
                <UButton color="neutral" variant="solid" @click="showPromptDetailsModal = false">
                  Close
                </UButton>
              </div>
            </template>
          </UCard>
        </template>
      </UModal>
    </div>
  </div>
</template>
