<script setup lang="ts">
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'
import type { GraphEdge } from '~/utils/graphLayout'

// The agents of an execution as a graph, like the one that built the experiment but read-only:
// nodes can't be connected, selecting one shows what it ran with.
const props = defineProps<{
  agents: readonly AgentExecutionSnapshot[]
}>()

const ordered = computed(() => [...props.agents].sort((a, b) => a.execution_order - b.execution_order))

function mappingsOf(snapshot: AgentExecutionSnapshot): AgentInputMapping[] {
  if (!snapshot.final_input_mappings)
    return []
  try {
    const parsed = JSON.parse(snapshot.final_input_mappings)
    return Array.isArray(parsed) ? parsed : []
  }
  catch {
    return []
  }
}

// The agents each one reads the output of, with the variables they feed it. Only earlier agents
// can be sources, so the graph has no cycle.
const dependencies = computed(() => {
  const list = ordered.value
  return new Map(list.map((snapshot, index) => {
    const carried = new Map<AgentExecutionSnapshot, string[]>()
    // An aggregator keeps the mappings of variables its formulas no longer read
    const used = snapshot.kind === 'aggregator' ? formulaVariables(parseSnapshotFormulas(snapshot)) : null
    for (const m of mappingsOf(snapshot).filter(m => m.source === 'agent' && (!used || used.includes(m.variable)))) {
      const source = list.slice(0, index).find(a => a.agent_id === m.sourceAgentId)
      if (source)
        carried.set(source, [...(carried.get(source) ?? []), m.variable])
    }
    return [snapshot, carried]
  }))
})

// Laid out by data flow, not run order: the canvas puts an agent one row under the lowest agent it
// reads from, and agents that don't depend on each other share a row.
const nodes = computed(() => ordered.value.map((snapshot, index) => ({
  id: `agent-${snapshot.id}`,
  snapshot,
  step: index + 1,
})))

// One edge per agent whose output another reads, labelled with the variables it feeds
const edges = computed<GraphEdge[]>(() => [...dependencies.value].flatMap(([snapshot, carried]) =>
  [...carried].map(([source, variables]) => ({
    id: `dep-${source.id}-${snapshot.id}`,
    source: `agent-${source.id}`,
    target: `agent-${snapshot.id}`,
    label: variables.join(', '),
    name: `${source.agent_name_snapshot} to ${snapshot.agent_name_snapshot}`,
    deletable: false,
  })),
))

const selectedId = ref<string | null>(null)
const selected = computed(() => ordered.value.find(a => `agent-${a.id}` === selectedId.value) ?? null)

// Opening the panel moves the focus to its heading, where a keyboard user starts reading
const heading = ref<HTMLElement>()
watch(heading, el => el?.focus({ preventScroll: true }), { flush: 'post' })

// w-96: the panel lies over the graph, which keeps clear of it
const PANEL_WIDTH = 384
</script>

<template>
  <!-- The panel overlays the graph rather than sitting beside it: the graph keeps its size, so
       nothing is left blank or redrawn while the panel slides in or out -->
  <GraphFrame label="Agents of this execution">
    <template #default="{ expanded, toggle }">
      <div class="relative size-full">
        <GraphCanvas
          :nodes="nodes"
          :edges="edges"
          :selected="selectedId"
          :inset-right="selected ? PANEL_WIDTH : 0"
          :label-of="node => node.snapshot.agent_name_snapshot"
          :scroll-pans="expanded"
          label="Agents of this execution"
          @select="id => selectedId = id"
        >
          <template #node="{ node, selected: isSelected }">
            <ExperimentsExecutionAgentNode :data="node" :selected="isSelected" />
          </template>

          <template #actions>
            <GraphControl
              :label="expanded ? 'Exit full screen' : 'Full screen'"
              :icon="expanded ? 'i-ph-arrows-in-simple-bold' : 'i-ph-arrows-out-simple-bold'"
              :kbd="expanded ? 'Esc' : undefined"
              @click="toggle"
            />
          </template>
        </GraphCanvas>

        <Transition
          enter-active-class="transition-[opacity,transform] duration-200 ease-out motion-reduce:transition-none"
          enter-from-class="opacity-0 translate-x-full"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition-[opacity,transform] duration-150 ease-out motion-reduce:transition-none"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-full"
        >
          <div v-if="selected" class="absolute inset-y-0 right-0 z-10 flex w-96 max-w-full flex-col border-l border-default bg-default shadow-lg">
            <header class="flex items-start justify-between gap-2 border-b border-default p-4">
              <div class="min-w-0">
                <h4 ref="heading" tabindex="-1" class="truncate text-sm font-semibold text-highlighted outline-none">
                  {{ selected.agent_name_snapshot }}
                </h4>
              </div>
              <UButton variant="ghost" size="sm" icon="i-ph-x-bold" color="neutral" aria-label="Close panel" @click="() => { selectedId = null }" />
            </header>
            <div class="flex-1 overflow-y-auto p-4">
              <ExperimentsAgentSnapshotDetails :snapshot="selected" :agents="ordered" />
            </div>
          </div>
        </Transition>
      </div>
    </template>
  </GraphFrame>
</template>
