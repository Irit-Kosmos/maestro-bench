<script setup lang="ts">
import type { Agent, AgentConfiguration, AgentInputMapping, Model, PromptVersion } from '~/types'

// The settings of one agent in an experiment: prompt, model, sampling and where each prompt variable gets its value.
// Shared by the list rows and the graph's side panel so both edit the same thing the same way.
const props = defineProps<{
  config: AgentConfiguration | undefined
  models: readonly Model[]
  promptVersions: readonly PromptVersion[]
  datasetHeaders: readonly string[]
  /** Agents whose output this agent may read, nearest last */
  upstreamAgents: readonly Agent[]
}>()

const emit = defineEmits<{
  update: [field: 'prompt_version_id' | 'model_id' | 'temperature' | 'max_tokens', value: number | undefined]
  setMapping: [mapping: AgentInputMapping]
  openPromptDetails: [promptVersionId: number]
}>()

const ids = useId()

// Flat, searchable, and the trigger always reads "Prompt name v1.2"
const promptItems = computed<any[]>(() => props.promptVersions
  .filter(v => v.is_active || v.id === props.config?.prompt_version_id)
  .map(v => ({
    label: `${v.prompt?.name || 'Unknown'} v${v.version}${v.is_default ? ' (default)' : ''}`,
    value: v.id,
  }))
  .sort((a, b) => a.label.localeCompare(b.label)))

// Grouped by provider; the current model stays selectable even if it was deactivated since
const modelItems = computed<any[]>(() => {
  const groups = new Map<string, { label: string, value: number }[]>()
  props.models
    .filter(m => m.is_active || m.id === props.config?.model_id)
    .forEach((m) => {
      const list = groups.get(m.provider) ?? []
      list.push({ label: m.name, value: m.id })
      groups.set(m.provider, list)
    })
  return [...groups.keys()].sort().flatMap((provider, index) => [
    ...(index > 0 ? [{ type: 'separator' as const }] : []),
    { type: 'label' as const, label: provider },
    ...groups.get(provider)!,
  ])
})

const selectedModel = computed(() => props.models.find(m => m.id === props.config?.model_id))

// Empty fields fall back to the model's own defaults, so say which
const temperaturePlaceholder = computed(() => selectedModel.value?.default_temperature?.toString() ?? 'Model default')
const maxTokensPlaceholder = computed(() => selectedModel.value?.default_max_tokens?.toString() ?? 'Model default')

function toNumber(value: string | number | undefined, parse: (s: string) => number) {
  if (value === '' || value === undefined)
    return undefined
  const parsed = parse(String(value))
  return Number.isNaN(parsed) ? undefined : parsed
}

// --- Variables ---

const variables = computed(() => {
  const versionId = props.config?.prompt_version_id
  return parsePromptVariables(props.promptVersions.find(v => v.id === versionId)?.variables)
})

const rows = computed(() => variables.value.map(variable => ({
  variable,
  mapping: props.config?.input_mappings?.find(m => m.variable === variable),
})))

const mappedCount = computed(() => rows.value.filter(row => isMappingComplete(row.mapping)).length)

const columnItems = computed(() => props.datasetHeaders.map(h => ({ label: h, value: h })))
const upstreamItems = computed(() => props.upstreamAgents.map(a => ({ label: a.name, value: a.id })))

// "Previous agent" only makes sense once something runs before this agent (unless it is already chosen)
function sourceItems(current: AgentInputMapping | undefined) {
  return [
    { label: 'Dataset column', value: 'dataset' },
    ...(props.upstreamAgents.length > 0 || current?.source === 'agent' ? [{ label: 'Previous agent', value: 'agent' }] : []),
    { label: 'Fixed text', value: 'static' },
  ]
}

function chooseSource(variable: string, source: AgentInputMapping['source']) {
  const existing = props.config?.input_mappings?.find(m => m.variable === variable)
  if (existing?.source === source)
    return
  const mapping: AgentInputMapping = { variable, source }
  // A dataset column is left for the user to pick: guessing the first one would be silently wrong
  if (source === 'agent') {
    // The nearest agent above is the usual source, and it's visible in the select
    mapping.sourceAgentId = props.upstreamAgents.at(-1)?.id
    mapping.sourceOutput = 'output'
  }
  else {
    mapping.staticValue = ''
  }
  emit('setMapping', mapping)
}

function patchMapping(row: (typeof rows.value)[number], patch: Partial<AgentInputMapping>) {
  if (row.mapping)
    emit('setMapping', { ...row.mapping, ...patch })
}
</script>

<template>
  <div class="@container flex flex-col gap-5">
    <div class="grid gap-4 @md:grid-cols-2">
      <UFormField label="Prompt version" required>
        <template v-if="config?.prompt_version_id" #hint>
          <UButton
            variant="link"
            color="neutral"
            size="xs"
            icon="i-lucide-eye"
            class="-my-1"
            @click="emit('openPromptDetails', config.prompt_version_id!)"
          >
            View
          </UButton>
        </template>
        <USelectMenu
          :model-value="config?.prompt_version_id"
          value-key="value"
          :items="promptItems"
          placeholder="Choose a prompt version"
          class="w-full"
          @update:model-value="(value) => emit('update', 'prompt_version_id', (value as number | undefined) ?? undefined)"
        />
      </UFormField>

      <UFormField label="Model" required>
        <USelectMenu
          :model-value="config?.model_id"
          value-key="value"
          :items="modelItems"
          placeholder="Choose a model"
          class="w-full"
          @update:model-value="(value) => emit('update', 'model_id', (value as number | undefined) ?? undefined)"
        />
      </UFormField>

      <UFormField label="Temperature" hint="Optional">
        <UInput
          :model-value="config?.temperature?.toString() ?? ''"
          type="number"
          inputmode="decimal"
          step="0.1"
          min="0"
          max="1"
          :placeholder="temperaturePlaceholder"
          class="w-full tabular-nums"
          @update:model-value="(value: string | number) => emit('update', 'temperature', toNumber(value, Number.parseFloat))"
        />
      </UFormField>

      <UFormField label="Max tokens" hint="Optional">
        <UInput
          :model-value="config?.max_tokens?.toString() ?? ''"
          type="number"
          inputmode="numeric"
          min="100"
          :placeholder="maxTokensPlaceholder"
          class="w-full tabular-nums"
          @update:model-value="(value: string | number) => emit('update', 'max_tokens', toNumber(value, s => Number.parseInt(s, 10)))"
        />
      </UFormField>
    </div>

    <!-- Variables -->
    <section v-if="rows.length > 0" :aria-labelledby="`${ids}-vars`">
      <div class="flex items-baseline justify-between gap-2">
        <h4 :id="`${ids}-vars`" class="text-sm font-medium text-highlighted">
          Prompt variables
        </h4>
        <span class="text-xs text-muted tabular-nums">{{ mappedCount }} of {{ rows.length }} mapped</span>
      </div>
      <p class="mt-0.5 text-sm text-muted">
        Where each variable of the prompt gets its value for every row.
      </p>

      <ul class="mt-3 divide-y divide-default rounded-lg border border-default">
        <li
          v-for="row in rows"
          :key="row.variable"
          class="grid items-center gap-2 px-3 py-2.5 @xl:grid-cols-[minmax(6rem,10rem)_11rem_minmax(0,1fr)]"
        >
          <code class="truncate font-mono text-xs text-highlighted" :title="row.variable">{{ row.variable }}</code>

          <USelect
            :model-value="row.mapping?.source"
            :items="sourceItems(row.mapping)"
            placeholder="Choose a source"
            size="sm"
            class="w-full"
            :aria-label="`Source for ${row.variable}`"
            :color="row.mapping ? 'neutral' : 'warning'"
            :highlight="!row.mapping"
            @update:model-value="(source) => chooseSource(row.variable, source as AgentInputMapping['source'])"
          />

          <div class="min-w-0">
            <USelect
              v-if="row.mapping?.source === 'dataset'"
              :model-value="row.mapping.sourceColumn"
              :items="columnItems"
              :disabled="columnItems.length === 0"
              :placeholder="columnItems.length === 0 ? 'Choose a dataset first' : 'Choose a column'"
              size="sm"
              class="w-full"
              :color="row.mapping.sourceColumn ? 'neutral' : 'warning'"
              :highlight="!row.mapping.sourceColumn"
              :aria-label="`Dataset column for ${row.variable}`"
              @update:model-value="(value: string) => patchMapping(row, { sourceColumn: value })"
            />
            <USelect
              v-else-if="row.mapping?.source === 'agent'"
              :model-value="row.mapping.sourceAgentId"
              :items="upstreamItems"
              placeholder="Choose an agent"
              size="sm"
              class="w-full"
              :color="row.mapping.sourceAgentId === undefined ? 'warning' : 'neutral'"
              :highlight="row.mapping.sourceAgentId === undefined"
              :aria-label="`Agent output for ${row.variable}`"
              @update:model-value="(value: number) => patchMapping(row, { sourceAgentId: value, sourceOutput: 'output' })"
            />
            <UInput
              v-else-if="row.mapping?.source === 'static'"
              :model-value="row.mapping.staticValue"
              placeholder="Text sent on every row"
              size="sm"
              class="w-full"
              :aria-label="`Fixed text for ${row.variable}`"
              @update:model-value="(value: string | number) => patchMapping(row, { staticValue: String(value) })"
            />
            <p v-else class="inline-flex items-center gap-1.5 text-xs text-warning">
              <UIcon name="i-lucide-triangle-alert" class="size-3.5 shrink-0" aria-hidden="true" />
              Not mapped yet
            </p>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
