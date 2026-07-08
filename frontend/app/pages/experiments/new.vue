<script setup lang="ts">
import type { AgentTeam, Dataset, Model, PromptVersion } from '~/types'
import { stepperItems } from '~/config/stepperConfig'

// Fetch data directly in the page
const { data: agentTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: models } = await useMyLazyFetch<Model[]>('/models')
const { data: allPromptVersions } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: datasets } = await useMyLazyFetch<Dataset[]>('/datasets')

// Composables
const { preview: datasetPreview, loadPreview } = useDatasetPreview()

// Custom composables - pass data as parameters
const experimentForm = useExperimentForm(agentTeams, allPromptVersions)
const agentManagement = useAgentManagement(agentTeams, allPromptVersions, models)
const stepperComposable = useExperimentStepper(allPromptVersions)
const submission = useExperimentSubmission()

// Destructure form state
const {
  experimentDetails,
  samplingConfig,
  agentConfigurations,
  selectedDataset,
  isStepValid,
  formValid,
  prepareExperimentData,
} = experimentForm

// Ref for the agent configuration step component (to access flow view)
const agentConfigRef = ref()

// Destructure agent management
const {
  updateAgentConfiguration,
} = agentManagement

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

// Dataset headers from preview
const datasetHeaders = computed(() => {
  return datasetPreview.value?.headers || []
})

// Watch for dataset changes to load preview
watch(selectedDataset, async (newDatasetId) => {
  if (newDatasetId) {
    await loadPreview(newDatasetId)
  }
})

// Page meta
useSeoMeta({
  title: 'Create New Experiment',
  description: 'Configure and launch a new MAESTRO experiment',
})

// Handlers
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
    // Compute execution order from the flow graph
    const executionOrder = agentConfigRef.value?.flowViewRef
      ? agentConfigRef.value.flowViewRef.computeExecutionOrder()
      : new Map<number, number>()

    const experimentData = prepareExperimentData({
      agentTeams: agentTeams.value || [],
      executionOrder,
    })

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
</script>

<template>
  <BasePageContent>
    <!-- Page Header -->
    <div class="mb-8">
      <h1 class="text-2xl font-bold text-neutral-900">
        Create New Experiment
      </h1>
      <p class="text-sm text-neutral-500 mt-1">
        Configure your experiment with prompt version and model selection
      </p>
    </div>

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
          :datasets="datasets"
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
          ref="agentConfigRef"
          :agent-configurations="agentConfigurations"
          :agent-teams="agentTeams"
          :models="models"
          :all-prompt-versions="allPromptVersions"
          :dataset-headers="datasetHeaders"
          @update-agent-config="updateAgentConfig"
          @open-prompt-details="openPromptDetails"
        />
      </template>
    </UStepper>

    <!-- Navigation Actions -->
    <div class="flex justify-between mt-8">
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

    <!-- Prompt Details Modal -->
    <ExperimentsPromptDetailsModal
      v-model:is-open="showPromptDetailsModal"
      :prompt-version-details="selectedPromptVersionForDetails"
    />
  </BasePageContent>
</template>
