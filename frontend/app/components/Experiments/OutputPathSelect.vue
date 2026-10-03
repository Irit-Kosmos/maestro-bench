<script setup lang="ts">
// Which part of an agent's JSON output a mapping reads: the whole output, or a dotted path
// suggested from what the agent returned in recent executions (any other path can be typed).
const props = defineProps<{
  agentId: number | undefined
  /** Label of the "whole output" choice */
  wholeLabel?: string
  /** Offer the paths to lists too (a score distribution), for formulas that reduce them */
  withLists?: boolean
}>()

const path = defineModel<string | undefined>({ default: undefined })

const WHOLE_OUTPUT = '__whole_output__'

const { pathsOf } = useAgentOutputPaths()
const promptVersions = inject(AGENT_PROMPT_VERSIONS, ref<Record<number, number | undefined>>({}))

// Suggestions come from runs of the source agent with the prompt version it has here:
// another version may answer in another shape
const known = computed(() => pathsOf(props.agentId, props.agentId === undefined ? undefined : promptVersions.value[props.agentId]))

const open = ref(false)
const typed = ref<string[]>([])

const items = computed(() => {
  const lists = new Set(props.withLists ? known.value?.list_paths : [])
  const paths = new Set([...(known.value?.paths ?? []), ...lists, ...typed.value])
  if (path.value)
    paths.add(path.value)
  const unseen = known.value !== null && known.value.paths.length + lists.size === 0
  return [
    { label: props.wholeLabel ?? '(whole output)', value: WHOLE_OUTPUT, list: false },
    ...[...paths].sort().map(p => ({ label: p, value: p, list: lists.has(p) })),
    ...(unseen ? [{ type: 'label' as const, label: 'No run with this prompt version yet: type a path' }] : []),
  ]
})

const selected = computed({
  get: () => path.value || WHOLE_OUTPUT,
  set: (value: string) => {
    path.value = value === WHOLE_OUTPUT ? '' : value
  },
})

function create(value: string) {
  const trimmed = value.trim()
  if (!trimmed)
    return
  typed.value.push(trimmed)
  path.value = trimmed
  open.value = false
}
</script>

<template>
  <USelectMenu
    v-model="selected"
    v-model:open="open"
    :items="items"
    value-key="value"
    create-item="always"
    :search-input="{ placeholder: 'Search or type a path…' }"
    :ui="{ value: 'font-mono text-xs' }"
    size="sm"
    @create="create"
  >
    <template #item-trailing="{ item }">
      <span v-if="(item as { list?: boolean }).list" class="text-xs text-muted" title="A list of values: reduce it with mean(), max(), sum()… or pick one item, like score.0">list</span>
    </template>
    <template #create-item-label="{ item }">
      Use <span class="font-mono text-xs">{{ item }}</span>
    </template>
  </USelectMenu>
</template>
