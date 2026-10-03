<script setup lang="ts">
import type { Edge, Node } from '@vue-flow/core'
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'

// The agents of an execution as a graph, like the one that built the experiment but read-only:
// nodes can't be moved or connected, selecting one shows what it ran with.
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

// Laid out by data flow, not run order: an agent sits one column right of the furthest agent it
// reads from, and agents that don't depend on each other share a column.
const COLUMN_GAP = 300
const ROW_GAP = 190
const nodes = computed<Node[]>(() => {
  const column = new Map<AgentExecutionSnapshot, number>()
  for (const snapshot of ordered.value) {
    const sources = [...(dependencies.value.get(snapshot)?.keys() ?? [])]
    column.set(snapshot, sources.length ? Math.max(...sources.map(s => column.get(s)! + 1)) : 0)
  }
  const columns = new Map<number, AgentExecutionSnapshot[]>()
  column.forEach((c, snapshot) => columns.set(c, [...(columns.get(c) ?? []), snapshot]))

  return ordered.value.map((snapshot, index) => {
    const c = column.get(snapshot)!
    const members = columns.get(c)!
    // Each column centred on the same line
    const row = members.indexOf(snapshot) - (members.length - 1) / 2
    return {
      id: `agent-${snapshot.id}`,
      type: 'agent',
      position: { x: c * COLUMN_GAP, y: row * ROW_GAP },
      data: { snapshot, step: index + 1 },
      draggable: false,
      connectable: false,
    }
  })
})

// One edge per agent whose output another reads, labelled with the variables it feeds
const edges = computed<Edge[]>(() => [...dependencies.value].flatMap(([snapshot, carried]) =>
  [...carried].map(([source, variables]) => ({
    id: `dep-${source.id}-${snapshot.id}`,
    source: `agent-${source.id}`,
    target: `agent-${snapshot.id}`,
    label: variables.join(', '),
    labelStyle: { fill: 'var(--ui-text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono, ui-monospace, monospace)' },
    labelBgStyle: { fill: 'var(--ui-bg)' },
    labelBgPadding: [4, 2] as [number, number],
    labelBgBorderRadius: 4,
  })),
))

const selectedId = ref<number | null>(null)
const selected = computed(() => ordered.value.find(a => a.id === selectedId.value) ?? null)

function onNodeClick(event: { node: Node }) {
  selectedId.value = (event.node.data as { snapshot: AgentExecutionSnapshot }).snapshot.id
}
</script>

<template>
  <!-- The panel overlays the graph rather than sitting beside it: the graph keeps its size, so
       nothing is left blank or redrawn while the panel slides in or out -->
  <div class="relative h-[500px] overflow-hidden rounded-lg border border-default bg-muted">
    <div class="size-full">
      <VueFlow
        :nodes="nodes"
        :edges="edges"
        :default-zoom="1"
        :min-zoom="0.2"
        :max-zoom="2"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :edges-updatable="false"
        :delete-key-code="null"
        :fit-view-on-init="true"
        @node-click="onNodeClick"
        @pane-click="() => { selectedId = null }"
      >
        <template #node-agent="nodeProps">
          <ExperimentsExecutionAgentNode v-bind="nodeProps" />
        </template>
        <VueFlowBackground pattern-color="var(--ui-border)" :gap="20" />
      </VueFlow>
    </div>

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
            <h4 class="truncate text-sm font-semibold text-highlighted">
              {{ selected.agent_name_snapshot }}
            </h4>
            <p v-if="selected.agent_team_name_snapshot && selected.agent_team_name_snapshot !== selected.agent_name_snapshot" class="mt-0.5 truncate text-xs text-muted">
              {{ selected.agent_team_name_snapshot }}
            </p>
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
