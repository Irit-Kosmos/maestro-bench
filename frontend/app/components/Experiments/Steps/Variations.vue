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
import type { PipelineItem } from '~/composables/useAgentPipeline'
import type { DatasetShape } from '~/composables/useDatasetShapes'
import type { AgentInputMapping, Dataset, DatasetAxisDraft, Model, PromptVersion, VariationDraft, VariationField } from '~/types'

// Turns the experiment into a batch: each variation is an axis (a step's model, prompt version or
// temperature and the values to try besides the current one), and one experiment runs per combination.
// The current setup is always one of the runs, so its value is part of every axis.
// The dataset is an axis too: the same setup on other datasets, whose columns stand for the base one's.
const props = defineProps<{
  /** Steps of the pipeline, in run order: an agent that runs twice is two steps, so two axes */
  items: readonly PipelineItem[]
  models?: readonly Model[] | null
  promptVersions?: readonly PromptVersion[] | null
  datasetHeaders?: readonly string[]
  /** Experiments the batch will start */
  count: number
  /** Name of the existing experiment the current setup was copied from, which is not run again */
  skippedOrigin?: string | null
  datasets?: readonly Dataset[] | null
  baseDatasetId?: number | null
  /** The base dataset is read under other column names (copied from a batch that varies the dataset) */
  datasetRenamed?: boolean
  /** Base columns the pipeline reads: every dataset of the axis needs a column for each */
  usedColumns?: readonly string[]
  shapeOf?: (id: number) => DatasetShape | undefined
  hasFailed?: (id: number) => boolean
  /** Datasets too short for the range of rows to run */
  tooShort?: readonly string[]
  /** Datasets of the axis that still have columns to match */
  unmatchedDatasets?: number
}>()

const emit = defineEmits<{
  setMapping: [stepKey: string, mapping: AgentInputMapping]
}>()

const variations = defineModel<VariationDraft[]>('variations', { required: true })
const datasetAxis = defineModel<DatasetAxisDraft | null>('datasetAxis', { default: null })

// Aggregators have no model, prompt or temperature to vary
const steps = computed(() => props.items.filter(item => item.config.is_active !== false && item.agent.kind !== 'aggregator'))
const multipleSteps = computed(() => steps.value.length > 1)
const stepItems = computed(() => steps.value.map(item => ({ label: item.label, value: item.key })))

// --- Dataset axis ---

const baseDataset = computed(() => props.datasets?.find(d => d.id === props.baseDatasetId))
const datasetExtras = computed(() => (datasetAxis.value?.extras ?? []).filter(id => id !== props.baseDatasetId))
// The base dataset is ticked and cannot be unticked, as the current value of the other axes
const datasetItems = computed(() => (props.datasets ?? []).map(d => ({ label: d.name, value: d.id, disabled: d.id === props.baseDatasetId })))
// The other datasets' columns stand for the base dataset's as it is on disk
const canVaryDataset = computed(() => !!props.baseDatasetId && !props.datasetRenamed)
const datasetValues = computed(() => props.baseDatasetId ? [props.baseDatasetId, ...datasetExtras.value] : datasetExtras.value)

function addDatasetAxis() {
  datasetAxis.value = { extras: [], picks: {} }
}

function setDatasets(selected: unknown) {
  if (!datasetAxis.value)
    return
  const extras = (selected as number[]).filter(id => id !== props.baseDatasetId)
  datasetAxis.value = { ...datasetAxis.value, extras }
}

function setPicks(id: number, picks: Record<string, string>) {
  if (datasetAxis.value)
    datasetAxis.value = { ...datasetAxis.value, picks: { ...datasetAxis.value.picks, [id]: picks } }
}

function datasetName(id: number) {
  return props.datasets?.find(d => d.id === id)?.name ?? `Dataset ${id}`
}

const issues = computed(() => variationIssues(variations.value))
const incomplete = computed(() => variations.value.some(v => v.extras.length === 0)
  || (datasetAxis.value !== null && datasetExtras.value.length === 0))
const anyAxis = computed(() => variations.value.length > 0 || datasetAxis.value !== null)

function baseOf(variation: VariationDraft) {
  return baseValue(steps.value.find(item => item.key === variation.step_key)?.config, variation.field)
}

// The current value is shown ticked and cannot be unticked: it is the setup the other values are compared to
function withBase(variation: VariationDraft): number[] {
  const base = baseOf(variation)
  return base === null ? variation.extras : [base, ...variation.extras]
}

function onlyAdded(variation: VariationDraft, selected: unknown): number[] {
  const base = baseOf(variation)
  return (selected as number[]).filter(value => value !== base)
}

// A prompt version with variables the step's prompt lacks says so: they get a mapping right below
function promptState(stepKey: string) {
  const config = steps.value.find(item => item.key === stepKey)?.config
  return (version: PromptVersion) => {
    const added = addedVariables({ step_key: stepKey, field: 'prompt_version_id', extras: [version.id] }, config, props.promptVersions ?? [])
    return added.length > 0 ? { description: `Adds ${added.join(', ')}` } : undefined
  }
}

// Variables the chosen prompts add to the step's own, and what they can read: the dataset and the steps before
function addedOf(variation: VariationDraft) {
  return addedVariables(variation, steps.value.find(item => item.key === variation.step_key)?.config, props.promptVersions ?? [])
}

function mappingsOf(stepKey: string) {
  return steps.value.find(item => item.key === stepKey)?.config.input_mappings
}

function upstreamOf(stepKey: string) {
  const index = props.items.findIndex(item => item.key === stepKey)
  return props.items.slice(0, Math.max(index, 0))
    .filter(item => item.config.is_active !== false)
    .map(item => ({ key: item.key, label: item.label, agent: item.agent }))
}

const unmappedCount = computed(() => variations.value.reduce((total, variation) => {
  const mapped = new Set((mappingsOf(variation.step_key) ?? []).filter(isMappingComplete).map(m => m.variable))
  return total + addedOf(variation).filter(variable => !mapped.has(variable)).length
}, 0))

function firstFreeField(stepKey: string): VariationField {
  const used = new Set(variations.value.filter(v => v.step_key === stepKey).map(v => v.field))
  return VARIATION_FIELDS.find(f => !used.has(f.value))?.value ?? 'model_id'
}

function add() {
  const stepKey = steps.value[0]?.key
  if (stepKey === undefined)
    return
  variations.value = [...variations.value, { step_key: stepKey, field: firstFreeField(stepKey), extras: [] }]
}

function patch(index: number, change: Partial<VariationDraft>) {
  variations.value = variations.value.map((v, i) => i === index ? { ...v, ...change } : v)
}

function remove(index: number) {
  variations.value = variations.value.filter((_, i) => i !== index)
}

function parseTemperatures(raw: string[]): number[] {
  const numbers = raw.map(value => Number(value.trim().replace(',', '.'))).filter(n => Number.isFinite(n) && n >= 0)
  return [...new Set(numbers)]
}

// A step can leave the pipeline while its variation is still listed
watch(steps, (list) => {
  const keys = new Set(list.map(item => item.key))
  if (variations.value.some(v => !keys.has(v.step_key)))
    variations.value = variations.value.filter(v => keys.has(v.step_key))
})
</script>

<template>
  <ExperimentsSection
    id="variations"
    title="Variations"
    description="Optional. Also run this setup with other models, prompts, temperatures or datasets: one experiment per combination, the current setup included."
  >
    <template v-if="anyAxis" #actions>
      <div class="flex gap-2">
        <UButton v-if="!datasetAxis" icon="i-ph-database-bold" color="neutral" variant="outline" size="xs" :disabled="!canVaryDataset" @click="addDatasetAxis">
          Vary the dataset
        </UButton>
        <UButton icon="i-ph-plus-bold" color="neutral" variant="outline" size="xs" :disabled="steps.length === 0" @click="add">
          Add a variation
        </UButton>
      </div>
    </template>

    <div v-if="!anyAxis">
      <div class="flex flex-wrap gap-2">
        <UButton
          icon="i-ph-arrows-split-bold"
          color="neutral"
          variant="outline"
          :disabled="steps.length === 0"
          @click="add"
        >
          Add a variation
        </UButton>
        <UButton
          icon="i-ph-database-bold"
          color="neutral"
          variant="outline"
          :disabled="!canVaryDataset"
          @click="addDatasetAxis"
        >
          Vary the dataset
        </UButton>
      </div>
      <p v-if="steps.length === 0 || !canVaryDataset" class="mt-2 text-xs text-muted">
        {{ !baseDatasetId ? 'Choose a dataset first.' : datasetRenamed ? 'This dataset is read under other column names: vary the dataset from the base experiment of its batch.' : 'Choose an agent first.' }}
      </p>
    </div>

    <div v-else class="flex flex-col gap-3">
      <ul class="flex flex-col gap-3">
        <li
          v-if="datasetAxis"
          class="enter-soft grid gap-3 rounded-lg border border-default p-3 sm:grid-cols-[minmax(0,10rem)_minmax(0,1fr)_auto]"
        >
          <p class="flex h-8 items-center gap-1.5 text-sm text-toned">
            <UIcon name="i-ph-database-bold" class="size-4 shrink-0 text-muted" aria-hidden="true" />
            Dataset
          </p>
          <USelectMenu
            :model-value="datasetValues"
            value-key="value"
            :items="datasetItems"
            multiple
            :placeholder="baseDataset ? `${baseDataset.name} and…` : 'Choose the datasets to run'"
            class="w-full"
            aria-label="Datasets to run"
            @update:model-value="setDatasets"
          />
          <UButton
            icon="i-ph-x-bold"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="Stop varying the dataset"
            @click="() => { datasetAxis = null }"
          />
          <div v-if="datasetExtras.length > 0" class="flex min-w-0 flex-col gap-2 sm:col-span-full">
            <ExperimentsDatasetColumns
              v-for="id in datasetExtras"
              :key="id"
              :name="datasetName(id)"
              :base-headers="datasetHeaders ?? []"
              :headers="shapeOf?.(id)?.headers"
              :failed="hasFailed?.(id)"
              :used="usedColumns ?? []"
              :picks="datasetAxis.picks[id] ?? {}"
              @update:picks="(picks) => setPicks(id, picks)"
            />
          </div>
        </li>
        <li
          v-for="(variation, index) in variations"
          :key="index"
          class="enter-soft grid gap-3 rounded-lg border border-default p-3 sm:grid-cols-[minmax(0,10rem)_minmax(0,10rem)_minmax(0,1fr)_auto]"
        >
          <USelectMenu
            v-if="multipleSteps"
            :model-value="variation.step_key"
            value-key="value"
            :items="stepItems"
            class="w-full"
            aria-label="Agent"
            @update:model-value="(key) => patch(index, { step_key: key as string, extras: [] })"
          />
          <p v-else class="flex h-8 items-center truncate text-sm text-toned">
            {{ steps[0]?.label }}
          </p>

          <USelectMenu
            :model-value="variation.field"
            value-key="value"
            :items="VARIATION_FIELDS"
            class="w-full"
            aria-label="Field to vary"
            @update:model-value="(field) => patch(index, { field: field as VariationField, extras: [] })"
          />

          <ModelsSelect
            v-if="variation.field === 'model_id'"
            :model-value="withBase(variation)"
            :models="models ?? []"
            multiple
            :locked-id="baseOf(variation)"
            placeholder="Choose the models to run"
            class="w-full"
            aria-label="Models to run"
            @update:model-value="(values) => patch(index, { extras: onlyAdded(variation, values) })"
          />
          <PromptsSelect
            v-else-if="variation.field === 'prompt_version_id'"
            :model-value="withBase(variation)"
            :prompt-versions="promptVersions ?? []"
            multiple
            :locked-id="baseOf(variation)"
            :item-state="promptState(variation.step_key)"
            placeholder="Choose the prompt versions to run"
            class="w-full"
            aria-label="Prompt versions to run"
            @update:model-value="(values) => patch(index, { extras: onlyAdded(variation, values) })"
          />
          <div v-else class="flex min-w-0 items-center gap-2">
            <UBadge
              color="neutral"
              variant="subtle"
              class="shrink-0"
              :label="`Current: ${baseOf(variation) ?? 'model default'}`"
            />
            <UInputTags
              :model-value="variation.extras.map(String)"
              placeholder="Add: 0, 0.5, 1 (Enter)"
              class="min-w-0 flex-1"
              aria-label="Other temperatures to run"
              @update:model-value="(raw) => patch(index, { extras: parseTemperatures(raw as string[]) })"
            />
          </div>

          <UButton
            icon="i-ph-x-bold"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="Remove variation"
            @click="remove(index)"
          />

          <div v-if="addedOf(variation).length > 0" class="@container min-w-0 sm:col-span-full">
            <ExperimentsVariableMappings
              :variables="addedOf(variation)"
              :mappings="mappingsOf(variation.step_key)"
              :dataset-headers="datasetHeaders ?? []"
              :upstream-steps="upstreamOf(variation.step_key)"
              title="Variables of these prompts"
              description="They use variables the current prompt does not have. Choose where each gets its value; the prompts that do not use one ignore it."
              @set-mapping="mapping => emit('setMapping', variation.step_key, mapping)"
            />
          </div>
        </li>
      </ul>

      <p class="text-sm" :class="count > BATCH_CONFIRM_THRESHOLD ? 'text-warning' : 'text-toned'" role="status">
        <template v-if="incomplete">
          Add at least one value besides the current one in each variation.
        </template>
        <template v-else-if="datasetAxis && datasetRenamed">
          This dataset is read under other column names: vary the dataset from the base experiment of its batch.
        </template>
        <template v-else-if="(unmatchedDatasets ?? 0) > 0">
          Match the columns of {{ unmatchedDatasets === 1 ? 'the dataset' : `the ${unmatchedDatasets} datasets` }} above.
        </template>
        <template v-else-if="(tooShort ?? []).length > 0">
          {{ tooShort!.join(', ') }} {{ tooShort!.length === 1 ? 'has' : 'have' }} fewer rows than where the range starts.
        </template>
        <template v-else-if="unmappedCount > 0">
          Map {{ unmappedCount === 1 ? 'the variable' : `the ${unmappedCount} variables` }} of the prompts above.
        </template>
        <template v-else>
          <span class="font-medium tabular-nums">{{ count }}</span>
          {{ count === 1 ? 'experiment' : 'experiments' }} will run at the same time<template v-if="skippedOrigin">
            (“{{ skippedOrigin }}” already exists and is not run again)
          </template><template v-if="count > BATCH_CONFIRM_THRESHOLD">
            — that is a lot of paid runs, you will be asked to confirm
          </template>.
        </template>
      </p>
      <ul v-if="issues.length > 0" class="flex flex-col gap-1 text-sm text-warning">
        <li v-for="issue in issues" :key="issue" class="flex items-start gap-1.5">
          <UIcon name="i-ph-warning-bold" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {{ issue }}
        </li>
      </ul>
    </div>
  </ExperimentsSection>
</template>
