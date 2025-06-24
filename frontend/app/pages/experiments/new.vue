<script setup lang="ts">
import { stepperItems } from '~/config/stepperConfig'

// Composables
const { preview: datasetPreview, loadPreview } = useDatasetPreview()

// Custom composables
const experimentForm = useExperimentForm()
const agentManagement = useAgentManagement()
const requestPreview = useRequestPreview()
const stepperComposable = useExperimentStepper()
const submission = useExperimentSubmission()

// Destructure form state
const {
  formData,
  experimentDetails,
  samplingConfig,
  requestConfig,
  selectedTeamId,
  agentConfigurations,
  selectedDataset,
  isStepValid,
  formValid,
  prepareExperimentData,
} = experimentForm

// Destructure agent management
const {
  selectTeam: selectTeamAction,
  updateAgentConfiguration,
} = agentManagement

// Destructure column mapping functions
// (none needed - implemented inline)

// Destructure stepper state and methods
const {
  currentStep,
  stepper,
  isSubmitting,
  showPromptDetailsModal,
  selectedPromptVersionForDetails,
  nextStep,
  prevStep,
  openPromptDetails,
} = stepperComposable

// Generate preview request
const selectedTeam = agentManagement.getSelectedTeam(selectedTeamId)
const previewRequest = requestPreview.generatePreviewRequest(
  selectedDataset,
  requestConfig,
  selectedTeam,
  agentConfigurations,
)

// Dataset headers from preview
const datasetHeaders = computed(() => {
  return datasetPreview.value?.headers || []
})

// Watch for dataset changes to load preview and set default column mappings
watch(selectedDataset, async (newDatasetId) => {
  if (newDatasetId) {
    await loadPreview(newDatasetId)
    // Set some default column mappings based on common column names
    if (requestConfig.value.columnMappings.length === 0) {
      const defaultMappings = []
      if (datasetHeaders.value.includes('question')) {
        defaultMappings.push({
          id: crypto.randomUUID(),
          sourceColumn: 'question',
          targetField: 'question',
        })
      }
      if (datasetHeaders.value.includes('desired_answer')) {
        defaultMappings.push({
          id: crypto.randomUUID(),
          sourceColumn: 'desired_answer',
          targetField: 'reference_answer',
        })
      }
      if (datasetHeaders.value.includes('student_answer')) {
        defaultMappings.push({
          id: crypto.randomUUID(),
          sourceColumn: 'student_answer',
          targetField: 'learner_answer',
        })
      }
      requestConfig.value.columnMappings = defaultMappings
    }
  }
})

// Page meta
useSeoMeta({
  title: 'Create New Experiment',
  description: 'Configure and launch a new MAESTRO experiment',
})

// Handlers
function selectTeam(teamId: number) {
  selectTeamAction(teamId, selectedTeamId, formData, agentConfigurations)
}

function updateAgentConfig(agentId: number, field: string, value: any) {
  if (field === 'reset') {
    // Handle reset case
    agentConfigurations.value[agentId] = value
  }
  else {
    updateAgentConfiguration(agentId, field, value, agentConfigurations)
  }
}

async function handleSubmit() {
  if (!formValid.value)
    return

  isSubmitting.value = true
  try {
    const experimentData = prepareExperimentData()

    const result = await submission.handleSubmit(experimentData)

    if (!result.success) {
      // Error was already handled in submission composable
    }
  }
  finally {
    isSubmitting.value = false
  }
}

async function handleCancel() {
  await submission.handleCancel()
}

// Helper functions for column mapping
function addMapping() {
  requestConfig.value.columnMappings.push({
    id: crypto.randomUUID(),
    sourceColumn: '',
    targetField: '',
  })
}

function removeMapping(id: string) {
  const index = requestConfig.value.columnMappings.findIndex(mapping => mapping.id === id)
  if (index > -1) {
    requestConfig.value.columnMappings.splice(index, 1)
  }
}

function updateMapping(id: string, field: 'sourceColumn' | 'targetField', value: string) {
  const mapping = requestConfig.value.columnMappings.find(m => m.id === id)
  if (mapping) {
    mapping[field] = value
  }
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
            class="w-full"
          >
            <!-- Step 1: Experiment Details -->
            <template #details>
              <ExperimentsStepsExperimentDetails
                :experiment-details="experimentDetails"
                @update:name="(value) => experimentDetails.name = value"
                @update:description="(value) => experimentDetails.description = value"
              />
            </template>

            <!-- Step 2: Dataset Selection -->
            <template #dataset>
              <ExperimentsStepsDatasetSelection
                :selected-dataset="selectedDataset"
                @update:selected-dataset="(value) => selectedDataset = value"
              />
            </template>

            <!-- Step 3: Dataset Sampling Configuration -->
            <template #sampling>
              <ExperimentsStepsDatasetSampling
                :selected-dataset="selectedDataset"
                :sampling-config="samplingConfig"
                @update:sampling-type="(value) => samplingConfig.sampling_type = value"
                @update:sampling-size="(value) => samplingConfig.sampling_size = value"
                @update:sampling-start-row="(value) => samplingConfig.sampling_start_row = value"
                @update:sampling-end-row="(value) => samplingConfig.sampling_end_row = value"
              />
            </template>

            <!-- Step 4: Agent Team & Configuration -->
            <template #agents>
              <ExperimentsStepsAgentConfiguration
                :selected-team-id="selectedTeamId"
                :agent-configurations="agentConfigurations"
                @select-team="selectTeam"
                @update-agent-config="updateAgentConfig"
                @open-prompt-details="openPromptDetails"
              />
            </template>

            <!-- Step 5: Request Configuration -->
            <template #request>
              <ExperimentsStepsRequestConfiguration
                :selected-dataset="selectedDataset"
                :request-config="requestConfig"
                :preview-request="previewRequest"
                :dataset-headers="datasetHeaders"
                @add-column-mapping="addMapping"
                @remove-column-mapping="removeMapping"
                @update-column-mapping="updateMapping"
              />
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
                :disabled="!isStepValid(currentStep)"
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
      <ExperimentsPromptDetailsModal
        v-model:is-open="showPromptDetailsModal"
        :prompt-version-details="selectedPromptVersionForDetails"
      />
    </div>
  </div>
</template>
