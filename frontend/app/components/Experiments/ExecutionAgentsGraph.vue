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

const nodes = computed<Node[]>(() => ordered.value.map((snapshot, index) => ({
  id: `agent-${snapshot.id}`,
  type: 'agent',
  position: { x: 50 + index * 280, y: 80 },
  data: { snapshot, step: index + 1 },
  draggable: false,
  connectable: false,
})))

// Solid: the run sequence. Dashed: an agent reading the output of one that isn't right before it.
const edges = computed<Edge[]>(() => {
  const list = ordered.value
  const result: Edge[] = []
  list.forEach((snapshot, index) => {
    const target = `agent-${snapshot.id}`
    const previous = list[index - 1]
    if (previous)
      result.push({ id: `seq-${previous.id}-${snapshot.id}`, source: `agent-${previous.id}`, target })

    const sources = new Set(mappingsOf(snapshot)
      .filter(m => m.source === 'agent')
      .map(m => list.slice(0, index).find(a => a.agent_id === m.sourceAgentId))
      .filter((a): a is AgentExecutionSnapshot => !!a && a.id !== previous?.id))
    sources.forEach((source) => {
      result.push({
        id: `dep-${source.id}-${snapshot.id}`,
        source: `agent-${source.id}`,
        target,
        style: { strokeDasharray: '5 4' },
      })
    })
  })
  return result
})

const selectedId = ref<number | null>(null)
const selected = computed(() => ordered.value.find(a => a.id === selectedId.value) ?? null)

function onNodeClick(event: { node: Node }) {
  selectedId.value = (event.node.data as { snapshot: AgentExecutionSnapshot }).snapshot.id
}
</script>

<template>
  <div class="flex h-[500px] overflow-hidden rounded-lg border border-default bg-muted">
    <div class="relative flex-1">
      <VueFlow
        :nodes="nodes"
        :edges="edges"
        :default-zoom="1"
        :min-zoom="0.2"
        :max-zoom="2"
        :fit-view-on-init="true"
        :nodes-draggable="false"
        :nodes-connectable="false"
        :edges-updatable="false"
        :delete-key-code="null"
        @node-click="onNodeClick"
        @pane-click="() => { selectedId = null }"
      >
        <template #node-agent="nodeProps">
          <ExperimentsExecutionAgentNode v-bind="nodeProps" />
        </template>
        <VueFlowBackground pattern-color="var(--ui-border)" :gap="20" />
        <VueFlowControls :show-interactive="false" />
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
      <div v-if="selected" class="flex h-full w-96 shrink-0 flex-col border-l border-default bg-default">
        <header class="flex items-start justify-between gap-2 border-b border-default p-4">
          <div class="min-w-0">
            <h4 class="truncate text-sm font-semibold text-highlighted">
              {{ selected.agent_name_snapshot }}
            </h4>
            <p v-if="selected.agent_team_name_snapshot && selected.agent_team_name_snapshot !== selected.agent_name_snapshot" class="mt-0.5 truncate text-xs text-muted">
              {{ selected.agent_team_name_snapshot }}
            </p>
          </div>
          <UButton variant="ghost" size="sm" icon="i-lucide-x" color="neutral" aria-label="Close panel" @click="() => { selectedId = null }" />
        </header>
        <div class="flex-1 overflow-y-auto p-4">
          <ExperimentsAgentSnapshotDetails :snapshot="selected" :agents="ordered" />
        </div>
      </div>
    </Transition>
  </div>
</template>
