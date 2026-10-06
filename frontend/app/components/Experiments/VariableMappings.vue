<script setup lang="ts">
import type { Agent, AgentInputMapping } from '~/types'

// Where each variable gets its value for every row: a dataset column, an earlier agent's output
// (whole, or one field of its JSON), or a fixed value. Shared by prompt variables and formula variables.
const props = withDefaults(defineProps<{
  variables: readonly string[]
  mappings: readonly AgentInputMapping[] | undefined
  datasetHeaders: readonly string[]
  /** Agents whose output may be read, nearest last */
  upstreamAgents: readonly Agent[]
  title: string
  description: string
  staticLabel?: string
  staticPlaceholder?: string
  isComplete?: (mapping: AgentInputMapping | undefined) => boolean
  /** Offer agent output fields that hold lists */
  withLists?: boolean
}>(), {
  staticLabel: 'Fixed text',
  staticPlaceholder: 'Text sent on every row',
  isComplete: isMappingComplete,
})

const emit = defineEmits<{
  setMapping: [mapping: AgentInputMapping]
  /** The variable under the pointer or focus, or null once it leaves */
  highlight: [variable: string | null]
}>()

const ids = useId()

const rows = computed(() => props.variables.map(variable => ({
  variable,
  mapping: props.mappings?.find(m => m.variable === variable),
})))

const mappedCount = computed(() => rows.value.filter(row => props.isComplete(row.mapping)).length)

const columnItems = computed(() => props.datasetHeaders.map(h => ({ label: h, value: h })))
const upstreamItems = computed(() => props.upstreamAgents.map(a => ({ label: a.name, value: a.id })))

// "Previous agent" only makes sense once something runs before this agent (unless it is already chosen)
function sourceItems(current: AgentInputMapping | undefined) {
  return [
    { label: 'Dataset column', value: 'dataset' },
    ...(props.upstreamAgents.length > 0 || current?.source === 'agent' ? [{ label: 'Previous agent', value: 'agent' }] : []),
    { label: props.staticLabel, value: 'static' },
  ]
}

const simplify = (name: string) => name.toLowerCase().replace(/[^a-z0-9]/g, '')

// The agent a variable most likely reads, shown in the select so a wrong guess is easy to see:
// one named like it ("content" or "c" for Content), else the nearest one no other variable reads yet
function defaultSourceAgent(variable: string): number | undefined {
  const candidates = props.upstreamAgents
  const name = simplify(variable)
  const named = candidates.find(a => simplify(a.name) === name)
    ?? (name ? candidates.find(a => simplify(a.name).startsWith(name)) : undefined)
  if (named)
    return named.id
  const taken = new Set((props.mappings ?? [])
    .filter(m => m.source === 'agent' && m.variable !== variable)
    .map(m => m.sourceAgentId))
  return [...candidates].reverse().find(a => !taken.has(a.id))?.id ?? candidates.at(-1)?.id
}

function chooseSource(variable: string, source: AgentInputMapping['source']) {
  const existing = props.mappings?.find(m => m.variable === variable)
  if (existing?.source === source)
    return
  const mapping: AgentInputMapping = { variable, source }
  // A dataset column is left for the user to pick: guessing the first one would be silently wrong
  if (source === 'agent') {
    mapping.sourceAgentId = defaultSourceAgent(variable)
    mapping.sourceOutput = 'output'
  }
  else if (source === 'static') {
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
  <section v-if="rows.length > 0" :aria-labelledby="`${ids}-vars`">
    <div class="flex items-baseline justify-between gap-2">
      <h4 :id="`${ids}-vars`" class="text-sm font-medium text-highlighted">
        {{ title }}
      </h4>
      <span class="text-xs text-muted tabular-nums">{{ mappedCount }} of {{ rows.length }} mapped</span>
    </div>
    <p class="mt-0.5 text-sm text-muted">
      {{ description }}
    </p>

    <ul class="mt-3 divide-y divide-default rounded-lg border border-default">
      <li
        v-for="row in rows"
        :key="row.variable"
        class="grid items-center gap-2 px-3 py-2.5 @xl:grid-cols-[minmax(6rem,10rem)_auto_11rem_minmax(0,1fr)]"
        @mouseenter="emit('highlight', row.variable)"
        @mouseleave="emit('highlight', null)"
        @focusin="emit('highlight', row.variable)"
        @focusout="emit('highlight', null)"
      >
        <code class="w-fit max-w-full truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="row.variable">{{ row.variable }}</code>
        <UIcon name="i-ph-arrow-right-bold" class="hidden size-3.5 shrink-0 text-dimmed @xl:block" aria-hidden="true" />

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
          <div v-else-if="row.mapping?.source === 'agent'" class="flex min-w-0 gap-2">
            <USelect
              :model-value="row.mapping.sourceAgentId"
              :items="upstreamItems"
              placeholder="Choose an agent"
              size="sm"
              class="min-w-0 flex-1"
              :color="row.mapping.sourceAgentId === undefined ? 'warning' : 'neutral'"
              :highlight="row.mapping.sourceAgentId === undefined"
              :aria-label="`Agent output for ${row.variable}`"
              @update:model-value="(value: number) => patchMapping(row, { sourceAgentId: value, sourceOutput: 'output', sourcePath: '' })"
            />
            <ExperimentsOutputPathSelect
              :model-value="row.mapping.sourcePath"
              :agent-id="row.mapping.sourceAgentId"
              whole-label="Whole output"
              :with-lists="withLists"
              class="min-w-0 flex-1"
              :aria-label="`Field of the output for ${row.variable}`"
              @update:model-value="(value: string | undefined) => patchMapping(row, { sourcePath: value ?? '' })"
            />
          </div>
          <UInput
            v-else-if="row.mapping?.source === 'static'"
            :model-value="row.mapping.staticValue"
            :placeholder="staticPlaceholder"
            size="sm"
            class="w-full"
            :color="isComplete(row.mapping) ? 'neutral' : 'warning'"
            :highlight="!isComplete(row.mapping)"
            :aria-label="`${staticLabel} for ${row.variable}`"
            @update:model-value="(value: string | number) => patchMapping(row, { staticValue: String(value) })"
          />
          <p v-else class="inline-flex items-center gap-1.5 text-xs text-warning">
            <UIcon name="i-ph-warning-bold" class="size-3.5 shrink-0" aria-hidden="true" />
            Not mapped yet
          </p>
        </div>
      </li>
    </ul>
  </section>
</template>
