<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Agent, Dataset, Experiment, Model, PromptVersion, VariationDraft } from '~/types'

definePageMeta({ requiresRole: 'editor' })

// Fetch data directly in the page
const { data: agents, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: models } = await useMyLazyFetch<Model[]>('/models')
const { data: allPromptVersions } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: datasets, refresh: refreshDatasets } = await useMyLazyFetch<Dataset[]>('/datasets')

// Composables
const { preview: datasetPreview, loadPreview } = useDatasetPreview()
const experimentForm = useExperimentForm(agents, allPromptVersions)
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

// Studies the new experiment (or batch) is put in once it starts
const studyIds = ref<number[]>([])

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
// A prompt variation can bring variables the agent's prompt does not have: they need a mapping too
const addedVariables = computed(() => addedVariablesByStep(variationDrafts.value, agentConfigurations.value, allPromptVersions.value ?? []))
const unmappedAdded = computed(() => unmappedAddedCount(addedVariables.value, agentConfigurations.value))
const variationsValid = computed(() =>
  !batchMode.value
  || (variationDrafts.value.every(draft => draft.extras.length > 0)
    && variationIssues(variationDrafts.value).length === 0
    && unmappedAdded.value === 0
    && experimentCount.value > 0),
)
const showConfirmBatch = ref(false)

const sourceCopied = ref(false)
watch([sourceExperiment, agents], ([source, list]) => {
  if (sourceCopied.value || !source || !list)
    return
  sourceCopied.value = true

  experimentDetails.value.name = source.batch_name || source.name
  selectedDataset.value = source.dataset_id
  samplingConfig.value = {
    sampling_type: source.sampling_type || 'all',
    sampling_size: source.sampling_size ?? undefined,
    sampling_start_row: source.sampling_start_row ?? undefined,
    sampling_end_row: source.sampling_end_row ?? undefined,
    // The same rows as the source, so that the runs can be compared row by row
    sampling_seed: source.sampling_type === 'random' ? source.sampling_seed ?? undefined : undefined,
  }
  agentConfigurations.value = Object.fromEntries((source.experiment_configs ?? [])
    .filter(config => config.is_active)
    .map(config => [config.step_key, {
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

// The agents preview their prompts with the first rows of the dataset
provide(DATASET_SAMPLE, computed(() => datasetPreview.value?.sample_data ?? []))

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
  agents,
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
  const toFix = agents.filter(item => pipeline.issuesOf(item.key).length > 0).length
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
        : `${agents.map(item => item.label).join(' → ')}${toFix > 0 ? ` · ${toFix} to fix` : ''}`,
      done: agentsValid.value,
      attention: agents.length > 0 && !agentsValid.value,
    },
    {
      id: 'variations' as const,
      label: 'Variations',
      value: !batchMode.value
        ? 'None, runs a single experiment'
        : unmappedAdded.value > 0
          ? `Map ${unmappedAdded.value === 1 ? 'a variable' : `${unmappedAdded.value} variables`} of the prompts`
          : experimentCount.value > 0
            ? `${experimentCount.value} ${experimentCount.value === 1 ? 'experiment' : 'experiments'}`
            : 'Add a value to each variation',
      done: variationsValid.value,
      attention: batchMode.value && !variationsValid.value,
    },
  ]
})

// Agents whose model has no key: the form is valid, but those runs would fail
const { lacksCredentials, missingKeyAdvice } = useProviderStatus()
const warnings = computed(() => {
  const labels = new Set<string>()
  for (const item of pipeline.items.value) {
    const model = models.value?.find(m => m.id === item.config.model_id)
    if (model && lacksCredentials(model.provider))
      labels.add(providerMeta(model.provider).label)
  }
  return [...labels].map(label => `No API key for ${label}: its runs will fail. ${missingKeyAdvice.value}`)
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
    const executionOrder = agentConfigRef.value?.getExecutionOrder() ?? new Map<string, number>()

    const experimentData = prepareExperimentData({ executionOrder })

    if (batchMode.value) {
      const { name, description, ...config } = experimentData
      await submission.handleBatchSubmit({
        name,
        description,
        base_experiment_id: sourceId ?? undefined,
        config,
        variations: variations.value,
        skip_base_point: skipBase.value,
      }, experimentCount.value, studyIds.value)
    }
    else {
      await submission.handleSubmit(experimentData, studyIds.value)
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
      <!-- The name and description are edited in place, as the page's title: no form section for them -->
      <header id="details" class="mb-8 scroll-mt-6">
        <p class="mb-2 text-sm text-muted">
          {{ batchMode ? 'New batch' : 'New experiment' }}<template v-if="sourceExperiment">
            · copied from
            <NuxtLink :to="`/experiments/${sourceExperiment.id}`" class="text-toned underline-offset-2 hover:underline">
              {{ sourceExperiment.name }}
            </NuxtLink>
          </template>
        </p>
        <ExperimentsStepsExperimentDetails
          :experiment-details="experimentDetails"
          :batch="batchMode"
          @update:name="(value) => experimentDetails.name = value"
          @update:description="(value) => experimentDetails.description = value"
        />
        <StudiesLaunchField v-model="studyIds" bare class="mt-3" />
      </header>

      <div class="grid gap-10 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        <div class="flex min-w-0 flex-col gap-8">
          <ExperimentsSection
            id="dataset"
            title="Dataset"
            description="Each row is one input for the agents."
          >
            <ExperimentsStepsDataset
              :selected-dataset="selectedDataset"
              :datasets="datasets"
              :refresh-datasets="refreshDatasets"
              :sampling-config="samplingConfig"
              @update:selected-dataset="(value) => selectedDataset = value"
              @update:sampling-type="(value) => samplingConfig.sampling_type = value"
              @update:sampling-size="(value) => samplingConfig.sampling_size = value"
              @update:sampling-start-row="(value) => samplingConfig.sampling_start_row = value"
              @update:sampling-end-row="(value) => samplingConfig.sampling_end_row = value"
              @update:sampling-seed="(value) => samplingConfig.sampling_seed = value"
            />
          </ExperimentsSection>

          <ExperimentsStepsAgentConfiguration
            ref="agentConfigRef"
            v-model:agent-configurations="agentConfigurations"
            :agents="agents"
            :models="models"
            :all-prompt-versions="allPromptVersions"
            :dataset-headers="datasetHeaders"
            :extra-variables="addedVariables"
            :refresh-agents="refreshAgents"
            @open-prompt-details="openPromptDetails"
          />

          <ExperimentsStepsVariations
            v-model:variations="variationDrafts"
            :items="pipeline.items.value"
            :models="models"
            :prompt-versions="allPromptVersions"
            :dataset-headers="datasetHeaders"
            :count="experimentCount"
            :skipped-origin="skipBase ? sourceExperiment?.name : null"
            @set-mapping="(key, mapping) => pipeline.setMapping(key, mapping)"
          />
        </div>

        <ExperimentsSummary
          :rows="summaryRows"
          :warnings="warnings"
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
