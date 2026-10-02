<script setup lang="ts">
import type { PipelineItem } from '~/composables/useAgentPipeline'
import type { Model, PromptVersion, VariationDraft, VariationField } from '~/types'

// Turns the experiment into a batch: each variation is an axis (an agent's model, prompt version or
// temperature and the values to try besides the current one), and one experiment runs per combination.
// The current setup is always one of the runs, so its value is part of every axis.
const props = defineProps<{
  /** Agents of the pipeline, in run order */
  items: readonly PipelineItem[]
  models?: readonly Model[] | null
  promptVersions?: readonly PromptVersion[] | null
  /** Experiments the batch will start */
  count: number
  /** Name of the existing experiment the current setup was copied from, which is not run again */
  skippedOrigin?: string | null
}>()

const variations = defineModel<VariationDraft[]>('variations', { required: true })

const agents = computed(() => props.items.filter(item => item.config.is_active !== false))
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

// A prompt version can replace the agent's one only if the agent's mappings cover its variables
function promptState(agentId: number) {
  const config = agents.value.find(item => item.agent.id === agentId)?.config
  return (version: PromptVersion) => {
    const missing = unmappedVariables(version, config)
    return missing.length > 0 ? { description: `Needs a mapping for ${missing.join(', ')}`, disabled: true } : undefined
  }
}

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
      <UButton icon="i-lucide-plus" color="neutral" variant="outline" size="xs" @click="add">
        Add a variation
      </UButton>
    </template>

    <div v-if="variations.length === 0">
      <UButton
        icon="i-lucide-split"
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
          class="grid gap-3 rounded-lg border border-default p-3 sm:grid-cols-[minmax(0,10rem)_minmax(0,10rem)_minmax(0,1fr)_auto]"
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
            icon="i-lucide-x"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="Remove variation"
            @click="remove(index)"
          />
        </li>
      </ul>

      <p class="text-sm" :class="count > BATCH_CONFIRM_THRESHOLD ? 'text-warning' : 'text-toned'" role="status">
        <template v-if="incomplete">
          Add at least one value besides the current one in each variation.
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
          <UIcon name="i-lucide-triangle-alert" class="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          {{ issue }}
        </li>
      </ul>
    </div>
  </ExperimentsSection>
</template>
