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
const agentManagement = useAgentManagement()
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

function removeAgentConfig(agentId: number) {
  delete agentConfigurations.value[agentId]
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

// ⌘↵ advances, and creates on the last step, without leaving the keyboard
defineShortcuts({
  meta_enter: {
    usingInput: true,
    handler: () => {
      if (stepper.value?.hasNext) {
        if (isStepValid.value(currentStep.value))
          nextStep()
      }
      else if (formValid.value && !isSubmitting.value) {
        handleSubmit()
      }
    },
  },
})
</script>

<template>
  <BasePageContent>
    <!-- Page Header + Stepper -->
    <div class="md:grid md:grid-cols-[1fr_auto] md:gap-x-8 md:gap-y-6 md:items-start mb-8">
      <div class="mb-6 md:mb-0">
        <h1 class="text-xl font-semibold text-highlighted">
          New experiment
        </h1>
        <p class="text-sm text-muted mt-0.5">
          Name it, pick a dataset, then choose the prompt and model for each agent.
        </p>
      </div>

      <!-- Stepper Component -->
      <UStepper
        ref="stepper"
        v-model="currentStep"
        :items="stepperItems"
        size="sm"
        class="w-full"
        :ui="{
          root: 'md:contents',
          header: 'md:col-start-2 md:row-start-1',
          content: 'md:col-span-2 md:row-start-2',
        }"
      >
        <!-- Step 1: Experiment Details -->
        <template #details>
          <ExperimentsStepsExperimentDetails
            class="enter-soft"
            :experiment-details="experimentDetails"
            @update:name="(value) => experimentDetails.name = value"
            @update:description="(value) => experimentDetails.description = value"
          />
        </template>

        <!-- Step 2: Dataset Selection & Sampling -->
        <template #dataset>
          <ExperimentsStepsDataset
            class="enter-soft"
            :selected-dataset="selectedDataset"
            :datasets="datasets"
            :sampling-config="samplingConfig"
            @update:selected-dataset="(value) => selectedDataset = value"
            @update:sampling-type="(value) => samplingConfig.sampling_type = value"
            @update:sampling-size="(value) => samplingConfig.sampling_size = value"
            @update:sampling-start-row="(value) => samplingConfig.sampling_start_row = value"
            @update:sampling-end-row="(value) => samplingConfig.sampling_end_row = value"
          />
        </template>

        <!-- Step 3: Agent Team & Configuration -->
        <template #agents>
          <ExperimentsStepsAgentConfiguration
            ref="agentConfigRef"
            class="enter-soft"
            :agent-configurations="agentConfigurations"
            :agent-teams="agentTeams"
            :models="models"
            :all-prompt-versions="allPromptVersions"
            :dataset-headers="datasetHeaders"
            @update-agent-config="updateAgentConfig"
            @remove-agent-config="removeAgentConfig"
            @open-prompt-details="openPromptDetails"
          />
        </template>
      </UStepper>
    </div>

    <!-- Navigation Actions -->
    <div class="flex items-center justify-between gap-3 mt-8 pt-4 border-t border-default">
      <UButton
        variant="ghost"
        color="neutral"
        @click="handleCancel"
      >
        Cancel
      </UButton>

      <div class="flex items-center gap-2">
        <UButton
          v-if="stepper?.hasPrev"
          variant="outline"
          color="neutral"
          icon="i-lucide-chevron-left"
          @click="prevStep"
        >
          Back
        </UButton>
        <UTooltip v-if="stepper?.hasNext" text="Next step" :kbds="['meta', 'enter']">
          <UButton
            trailing-icon="i-lucide-chevron-right"
            :disabled="!isStepValid(currentStep)"
            @click="nextStep"
          >
            Next
          </UButton>
        </UTooltip>
        <UTooltip v-else text="Create and start" :kbds="['meta', 'enter']">
          <UButton
            color="primary"
            icon="i-lucide-play"
            :disabled="!formValid"
            :loading="isSubmitting"
            @click="handleSubmit"
          >
            Create and start
          </UButton>
        </UTooltip>
      </div>
    </div>

    <!-- Prompt Details Modal -->
    <ExperimentsPromptDetailsModal
      v-model:is-open="showPromptDetailsModal"
      :prompt-version-details="selectedPromptVersionForDetails"
    />
  </BasePageContent>
</template>
