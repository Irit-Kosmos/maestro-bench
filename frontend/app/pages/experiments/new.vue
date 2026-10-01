<script setup lang="ts">
import type { AgentTeam, Dataset, Model, PromptVersion } from '~/types'

// Fetch data directly in the page
const { data: agentTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: models } = await useMyLazyFetch<Model[]>('/models')
const { data: allPromptVersions } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: datasets } = await useMyLazyFetch<Dataset[]>('/datasets')

// Composables
const { preview: datasetPreview, loadPreview } = useDatasetPreview()
const experimentForm = useExperimentForm(agentTeams, allPromptVersions)
const submission = useExperimentSubmission()
const promptDetails = usePromptDetailsModal(allPromptVersions)

const {
  experimentDetails,
  samplingConfig,
  agentConfigurations,
  selectedDataset,
  detailsValid,
  datasetValid,
  agentsValid,
  formValid,
  prepareExperimentData,
} = experimentForm

const {
  showPromptDetailsModal,
  selectedPromptVersionForDetails,
  openPromptDetails,
} = promptDetails

const isSubmitting = ref(false)

// Ref for the agent configuration section (to read the run order)
const agentConfigRef = ref()

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

// --- Summary ---

// Same derivation as the agents section, to name the agents in run order
const pipeline = useAgentPipeline({
  agentTeams,
  configurations: agentConfigurations,
  promptVersions: allPromptVersions,
  datasetHeaders,
})

const samplingLabel = computed(() => {
  const { sampling_type, sampling_size, sampling_start_row, sampling_end_row } = samplingConfig.value
  if (sampling_type === 'random')
    return `${sampling_size ?? '?'} random rows`
  if (sampling_type === 'range')
    return `rows ${sampling_start_row ?? '?'}–${sampling_end_row ?? '?'}`
  return 'all rows'
})

const summaryRows = computed(() => {
  const agents = pipeline.items.value
  const toFix = agents.filter(item => pipeline.issuesOf(item.agent.id).length > 0).length
  const dataset = datasets.value?.find(d => d.id === selectedDataset.value)

  return [
    {
      id: 'details' as const,
      label: 'Name',
      value: experimentDetails.value.name.trim() || 'Required',
      done: detailsValid.value,
    },
    {
      id: 'dataset' as const,
      label: 'Dataset',
      value: !dataset
        ? 'Choose a dataset'
        : datasetValid.value ? `${dataset.name} · ${samplingLabel.value}` : `${dataset.name} · complete the sampling`,
      done: datasetValid.value,
      attention: !!dataset && !datasetValid.value,
    },
    {
      id: 'agents' as const,
      label: agents.length > 1 ? `Agents · ${agents.length}` : 'Agent',
      value: agents.length === 0
        ? 'Choose an agent'
        : `${agents.map(item => item.agent.name).join(' → ')}${toFix > 0 ? ` · ${toFix} to fix` : ''}`,
      done: agentsValid.value,
      attention: agents.length > 0 && !agentsValid.value,
    },
  ]
})

// The first section that still needs something, for the shortcut and the "jump" rows
const firstIncomplete = computed(() => summaryRows.value.find(row => !row.done)?.id)

// Scrolls only the panel that scrolls: scrollIntoView would also move the shell's fixed containers
function scrollParentOf(el: HTMLElement) {
  for (let parent = el.parentElement; parent; parent = parent.parentElement) {
    const { overflowY } = getComputedStyle(parent)
    if ((overflowY === 'auto' || overflowY === 'scroll') && parent.scrollHeight > parent.clientHeight)
      return parent
  }
  return null
}

function jumpTo(id: 'details' | 'dataset' | 'agents') {
  const section = document.getElementById(id)
  const scroller = section && scrollParentOf(section)
  if (section && scroller) {
    const top = section.getBoundingClientRect().top - scroller.getBoundingClientRect().top + scroller.scrollTop
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    scroller.scrollTo({ top: Math.max(top - 24, 0), behavior: reduceMotion ? 'auto' : 'smooth' })
  }
  if (id === 'details')
    document.getElementById('experiment-name')?.focus({ preventScroll: true })
}

// --- Handlers ---

async function handleSubmit() {
  if (!formValid.value || isSubmitting.value)
    return

  isSubmitting.value = true
  try {
    // Run order, as shown in the list or wired in the graph
    const executionOrder = agentConfigRef.value?.getExecutionOrder() ?? new Map<number, number>()

    const experimentData = prepareExperimentData({
      agentTeams: agentTeams.value || [],
      executionOrder,
    })

    await submission.handleSubmit(experimentData)
  }
  finally {
    isSubmitting.value = false
  }
}

async function handleCancel() {
  await submission.handleCancel()
}

// ⌘↵ creates; when something is missing it takes you there instead
defineShortcuts({
  meta_enter: {
    usingInput: true,
    handler: () => {
      if (formValid.value)
        handleSubmit()
      else if (firstIncomplete.value)
        jumpTo(firstIncomplete.value)
    },
  },
})
</script>

<template>
  <BasePageContent>
    <div class="mx-auto max-w-6xl pb-6">
      <div class="mb-8">
        <h1 class="text-xl font-semibold text-highlighted">
          New experiment
        </h1>
        <p class="text-sm text-muted mt-0.5">
          Name it, pick a dataset, then choose the agents to run.
        </p>
      </div>

      <div class="grid gap-10 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        <div class="flex min-w-0 flex-col gap-8">
          <ExperimentsSection id="details" title="Details">
            <ExperimentsStepsExperimentDetails
              :experiment-details="experimentDetails"
              @update:name="(value) => experimentDetails.name = value"
              @update:description="(value) => experimentDetails.description = value"
            />
          </ExperimentsSection>

          <ExperimentsSection
            id="dataset"
            title="Dataset"
            description="Each row is one input for the agents. Open a preview to check the columns."
          >
            <ExperimentsStepsDataset
              :selected-dataset="selectedDataset"
              :datasets="datasets"
              :sampling-config="samplingConfig"
              @update:selected-dataset="(value) => selectedDataset = value"
              @update:sampling-type="(value) => samplingConfig.sampling_type = value"
              @update:sampling-size="(value) => samplingConfig.sampling_size = value"
              @update:sampling-start-row="(value) => samplingConfig.sampling_start_row = value"
              @update:sampling-end-row="(value) => samplingConfig.sampling_end_row = value"
            />
          </ExperimentsSection>

          <ExperimentsStepsAgentConfiguration
            ref="agentConfigRef"
            v-model:agent-configurations="agentConfigurations"
            :agent-teams="agentTeams"
            :models="models"
            :all-prompt-versions="allPromptVersions"
            :dataset-headers="datasetHeaders"
            @open-prompt-details="openPromptDetails"
          />
        </div>

        <ExperimentsSummary
          :rows="summaryRows"
          :can-submit="formValid"
          :submitting="isSubmitting"
          @jump="jumpTo"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
      </div>
    </div>

    <!-- Prompt Details Modal -->
    <ExperimentsPromptDetailsModal
      v-model:is-open="showPromptDetailsModal"
      :prompt-version-details="selectedPromptVersionForDetails"
    />
  </BasePageContent>
</template>
