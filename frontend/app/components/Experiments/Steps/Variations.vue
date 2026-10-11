<script setup lang="ts">
import type { PipelineItem } from '~/composables/useAgentPipeline'
import type { AgentInputMapping, Model, PromptVersion, VariationDraft, VariationField } from '~/types'

// Turns the experiment into a batch: each variation is an axis (an agent's model, prompt version or
// temperature and the values to try besides the current one), and one experiment runs per combination.
// The current setup is always one of the runs, so its value is part of every axis.
const props = defineProps<{
  /** Agents of the pipeline, in run order */
  items: readonly PipelineItem[]
  models?: readonly Model[] | null
  promptVersions?: readonly PromptVersion[] | null
  datasetHeaders?: readonly string[]
  /** Experiments the batch will start */
  count: number
  /** Name of the existing experiment the current setup was copied from, which is not run again */
  skippedOrigin?: string | null
}>()

const emit = defineEmits<{
  setMapping: [agentId: number, mapping: AgentInputMapping]
}>()

const variations = defineModel<VariationDraft[]>('variations', { required: true })

// Aggregators have no model, prompt or temperature to vary
const agents = computed(() => props.items.filter(item => item.config.is_active !== false && item.agent.kind !== 'aggregator'))
const multipleAgents = computed(() => agents.value.length > 1)
const agentItems = computed(() => agents.value.map(item => ({ label: item.agent.name, value: item.agent.id })))

const issues = computed(() => variationIssues(variations.value))
const incomplete = computed(() => variations.value.some(v => v.extras.length === 0))

function baseOf(variation: VariationDraft) {
  return baseValue(agents.value.find(item => item.agent.id === variation.agent_id)?.config, variation.field)
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

// A prompt version with variables the agent's prompt lacks says so: they get a mapping right below
function promptState(agentId: number) {
  const config = agents.value.find(item => item.agent.id === agentId)?.config
  return (version: PromptVersion) => {
    const added = addedVariables({ agent_id: agentId, field: 'prompt_version_id', extras: [version.id] }, config, props.promptVersions ?? [])
    return added.length > 0 ? { description: `Adds ${added.join(', ')}` } : undefined
  }
}

// Variables the chosen prompts add to the agent's own, and what they can read: the dataset and the agents before
function addedOf(variation: VariationDraft) {
  return addedVariables(variation, agents.value.find(item => item.agent.id === variation.agent_id)?.config, props.promptVersions ?? [])
}

function mappingsOf(agentId: number) {
  return agents.value.find(item => item.agent.id === agentId)?.config.input_mappings
}

function upstreamOf(agentId: number) {
  const index = props.items.findIndex(item => item.agent.id === agentId)
  return props.items.slice(0, Math.max(index, 0))
    .filter(item => item.config.is_active !== false)
    .map(item => item.agent)
}

const unmappedCount = computed(() => variations.value.reduce((total, variation) => {
  const mapped = new Set((mappingsOf(variation.agent_id) ?? []).filter(isMappingComplete).map(m => m.variable))
  return total + addedOf(variation).filter(variable => !mapped.has(variable)).length
}, 0))

function firstFreeField(agentId: number): VariationField {
  const used = new Set(variations.value.filter(v => v.agent_id === agentId).map(v => v.field))
  return VARIATION_FIELDS.find(f => !used.has(f.value))?.value ?? 'model_id'
}

function add() {
  const agentId = agents.value[0]?.agent.id
  if (agentId === undefined)
    return
  variations.value = [...variations.value, { agent_id: agentId, field: firstFreeField(agentId), extras: [] }]
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

// An agent can leave the pipeline while its variation is still listed
watch(agents, (list) => {
  const ids = new Set(list.map(item => item.agent.id))
  if (variations.value.some(v => !ids.has(v.agent_id)))
    variations.value = variations.value.filter(v => ids.has(v.agent_id))
})
</script>

<template>
  <ExperimentsSection
    id="variations"
    title="Variations"
    description="Optional. Also run this setup with other models, prompts or temperatures: one experiment per combination, the current setup included."
  >
    <template v-if="variations.length > 0" #actions>
      <UButton icon="i-ph-plus-bold" color="neutral" variant="outline" size="xs" @click="add">
        Add a variation
      </UButton>
    </template>

    <div v-if="variations.length === 0">
      <UButton
        icon="i-ph-arrows-split-bold"
        color="neutral"
        variant="outline"
        :disabled="agents.length === 0"
        @click="add"
      >
        Add a variation
      </UButton>
      <p v-if="agents.length === 0" class="mt-2 text-xs text-muted">
        Choose an agent first.
      </p>
    </div>

    <div v-else class="flex flex-col gap-3">
      <ul class="flex flex-col gap-3">
        <li
          v-for="(variation, index) in variations"
          :key="index"
          class="enter-soft grid gap-3 rounded-lg border border-default p-3 sm:grid-cols-[minmax(0,10rem)_minmax(0,10rem)_minmax(0,1fr)_auto]"
        >
          <USelectMenu
            v-if="multipleAgents"
            :model-value="variation.agent_id"
            value-key="value"
            :items="agentItems"
            class="w-full"
            aria-label="Agent"
            @update:model-value="(id) => patch(index, { agent_id: id as number, extras: [] })"
          />
          <p v-else class="flex h-8 items-center truncate text-sm text-toned">
            {{ agents[0]?.agent.name }}
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
            :item-state="promptState(variation.agent_id)"
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
              :mappings="mappingsOf(variation.agent_id)"
              :dataset-headers="datasetHeaders ?? []"
              :upstream-agents="upstreamOf(variation.agent_id)"
              title="Variables of these prompts"
              description="They use variables the current prompt does not have. Choose where each gets its value; the prompts that do not use one ignore it."
              @set-mapping="mapping => emit('setMapping', variation.agent_id, mapping)"
            />
          </div>
        </li>
      </ul>

      <p class="text-sm" :class="count > BATCH_CONFIRM_THRESHOLD ? 'text-warning' : 'text-toned'" role="status">
        <template v-if="incomplete">
          Add at least one value besides the current one in each variation.
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
