<script setup lang="ts">
import type { AgentTeam, Dataset, Experiment, Model, PromptVersion, VariationDraft } from '~/types'

definePageMeta({ requiresRole: 'editor' })

// Fetch data directly in the page
const { data: agentTeams, refresh: refreshAgentTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
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

// --- Starting from an existing experiment: ?from=<id> copies its setup ---

const route = useRoute()
const fromId = Number(route.query.from)
const sourceId = Number.isFinite(fromId) && fromId > 0 ? fromId : null
const { data: sourceExperiment } = sourceId
  ? await useMyLazyFetch<Experiment>(`/experiments/${sourceId}`)
  : { data: ref<Experiment | null>(null) }

// --- Variations: more than none makes it a batch ---

// A batch is an experiment with at least one variation. The current setup is one of its runs,
// except when it was copied from an experiment that is still unchanged: that one already exists.
const variationDrafts = ref<VariationDraft[]>([])
const batchMode = computed(() => variationDrafts.value.length > 0)
const variations = computed(() => resolveVariations(variationDrafts.value, agentConfigurations.value))
const skipBase = computed(() => batchMode.value && !!sourceExperiment.value
  && formSignature(selectedDataset.value, samplingConfig.value, agentConfigurations.value) === experimentSignature(sourceExperiment.value))
const experimentCount = computed(() => variationCount(variations.value, skipBase.value))
const variationsValid = computed(() =>
  !batchMode.value
  || (variationDrafts.value.every(draft => draft.extras.length > 0)
    && variationIssues(variationDrafts.value).length === 0
    && experimentCount.value > 0),
)
const showConfirmBatch = ref(false)

const sourceCopied = ref(false)
watch([sourceExperiment, agentTeams], ([source, teams]) => {
  if (sourceCopied.value || !source || !teams)
    return
  sourceCopied.value = true

  experimentDetails.value.name = source.batch_name || source.name
  selectedDataset.value = source.dataset_id
  samplingConfig.value = {
    sampling_type: source.sampling_type || 'all',
    sampling_size: source.sampling_size ?? undefined,
    sampling_start_row: source.sampling_start_row ?? undefined,
    sampling_end_row: source.sampling_end_row ?? undefined,
  }
  agentConfigurations.value = Object.fromEntries((source.experiment_configs ?? [])
    .filter(config => config.is_active)
    .map(config => [config.agent_id, {
      prompt_version_id: config.prompt_version_id ?? undefined,
      model_id: config.model_id ?? undefined,
      temperature: config.temperature ?? undefined,
      max_tokens: config.max_tokens ?? undefined,
      is_active: true,
      execution_order: config.execution_order,
      input_mappings: config.input_mappings ?? [],
      ...(config.formulas ? { formulas: config.formulas } : {}),
    }]))
}, { immediate: true })

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
}, { immediate: true })

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
      label: batchMode.value ? 'Batch name' : 'Name',
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
    {
      id: 'variations' as const,
      label: 'Variations',
      value: !batchMode.value
        ? 'None, runs a single experiment'
        : experimentCount.value > 0
          ? `${experimentCount.value} ${experimentCount.value === 1 ? 'experiment' : 'experiments'}`
          : 'Add a value to each variation',
      done: variationsValid.value,
      attention: batchMode.value && !variationsValid.value,
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

function jumpTo(id: 'details' | 'dataset' | 'agents' | 'variations') {
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

const canSubmit = computed(() => formValid.value && variationsValid.value)

// A large batch is a lot of paid runs at once: ask first
function handleSubmit() {
  if (!canSubmit.value || isSubmitting.value)
    return
  if (batchMode.value && experimentCount.value > BATCH_CONFIRM_THRESHOLD)
    showConfirmBatch.value = true
  else
    submit()
}

async function submit() {
  showConfirmBatch.value = false
  if (!canSubmit.value || isSubmitting.value)
    return

  isSubmitting.value = true
  try {
    // Run order, as shown in the list or wired in the graph
    const executionOrder = agentConfigRef.value?.getExecutionOrder() ?? new Map<number, number>()

    const experimentData = prepareExperimentData({
      agentTeams: agentTeams.value || [],
      executionOrder,
    })

    if (batchMode.value) {
      const { name, description, ...config } = experimentData
      await submission.handleBatchSubmit({
        name,
        description,
        base_experiment_id: sourceId ?? undefined,
        config,
        variations: variations.value,
        skip_base_point: skipBase.value,
      }, experimentCount.value)
    }
    else {
      await submission.handleSubmit(experimentData)
    }
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
      if (canSubmit.value)
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
          {{ batchMode ? 'New batch' : 'New experiment' }}
        </h1>
        <p class="text-sm text-muted mt-0.5">
          <template v-if="sourceExperiment">
            Copied from
            <NuxtLink :to="`/experiments/${sourceExperiment.id}`" class="text-toned underline-offset-2 hover:underline">
              {{ sourceExperiment.name }}
            </NuxtLink>.
            Add a variation to run it with other models, prompts or temperatures.
          </template>
          <template v-else>
            Name it, pick a dataset, then choose the agents to run.
          </template>
        </p>
      </div>

      <div class="grid gap-10 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        <div class="flex min-w-0 flex-col gap-8">
          <ExperimentsSection id="details" title="Details">
            <ExperimentsStepsExperimentDetails
              :experiment-details="experimentDetails"
              :batch="batchMode"
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
            :refresh-agents="refreshAgentTeams"
            @open-prompt-details="openPromptDetails"
          />

          <ExperimentsStepsVariations
            v-model:variations="variationDrafts"
            :items="pipeline.items.value"
            :models="models"
            :prompt-versions="allPromptVersions"
            :count="experimentCount"
            :skipped-origin="skipBase ? sourceExperiment?.name : null"
          />
        </div>

        <ExperimentsSummary
          :rows="summaryRows"
          :can-submit="canSubmit"
          :submit-label="batchMode ? (experimentCount > 0 ? `Start ${experimentCount} ${experimentCount === 1 ? 'experiment' : 'experiments'}` : 'Start batch') : 'Create and start'"
          :submitting="isSubmitting"
          @jump="jumpTo"
          @submit="handleSubmit"
          @cancel="handleCancel"
        />
      </div>
    </div>

    <UModal v-model:open="showConfirmBatch" title="Start this batch?">
      <template #body>
        <p class="text-sm text-toned text-pretty">
          This starts <span class="font-medium tabular-nums">{{ experimentCount }}</span> experiments at once, each one running the whole sample.
          Check the number of rows and the models first: it can be a lot of API calls.
        </p>
      </template>
      <template #footer>
        <div class="flex w-full justify-end gap-3">
          <UButton variant="outline" color="neutral" @click="() => { showConfirmBatch = false }">
            Not yet
          </UButton>
          <UButton :loading="isSubmitting" @click="submit">
            Start {{ experimentCount }} experiments
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- Prompt Details Modal -->
    <ExperimentsPromptDetailsModal
      v-model:is-open="showPromptDetailsModal"
      :prompt-version-details="selectedPromptVersionForDetails"
    />
  </BasePageContent>
</template>
