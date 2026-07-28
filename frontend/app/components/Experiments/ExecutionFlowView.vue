<script setup lang="ts">
import type { Edge, Node } from '@vue-flow/core'
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'
import { useVueFlow } from '@vue-flow/core'

interface Position {
  x: number
  y: number
}

export interface ExecutionFlowViewProps {
  agentExecutions: AgentExecutionSnapshot[]
}

const props = defineProps<ExecutionFlowViewProps>()

// Vue Flow instance
const { fitView } = useVueFlow()

const nodes = ref<Node[]>([])
const edges = ref<Edge[]>([])

function parseInputMappings(snapshot: AgentExecutionSnapshot): AgentInputMapping[] {
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

function computeLayout(executions: AgentExecutionSnapshot[]) {
  // Group by execution_order for horizontal layout
  const orderGroups = new Map<number, AgentExecutionSnapshot[]>()
  executions.forEach((snapshot) => {
    const order = snapshot.execution_order || 1
    if (!orderGroups.has(order)) {
      orderGroups.set(order, [])
    }
    orderGroups.get(order)!.push(snapshot)
  })

  const sortedOrders = [...orderGroups.keys()].sort((a, b) => a - b)
  const positions = new Map<number, Position>()

  sortedOrders.forEach((order, orderIndex) => {
    const group = orderGroups.get(order)!
    const x = 50 + orderIndex * 280
    group.forEach((snapshot, index) => {
      const y = 50 + index * 160
      positions.set(snapshot.agent_id, { x, y })
    })
  })

  return positions
}

function buildFlow(executions: AgentExecutionSnapshot[]) {
  if (!executions.length) {
    nodes.value = []
    edges.value = []
    return
  }

  const positions = computeLayout(executions)

  nodes.value = executions.map((snapshot) => {
    const position = positions.get(snapshot.agent_id) || { x: 50, y: 50 }
    return {
      id: `agent-${snapshot.agent_id}`,
      type: 'execution-agent',
      position,
      data: { snapshot },
    }
  })

  const builtEdges: Edge[] = []
  const edgeIds = new Set<string>()

  function addEdge(edge: Edge) {
    if (edgeIds.has(edge.id))
      return
    edgeIds.add(edge.id)
    builtEdges.push(edge)
  }

  // 1. Edges from agent-to-agent input mappings (data dependencies)
  executions.forEach((snapshot) => {
    const mappings = parseInputMappings(snapshot)
    mappings.forEach((mapping) => {
      if (mapping.source === 'agent' && mapping.sourceAgentId) {
        const sourceId = `agent-${mapping.sourceAgentId}`
        const targetId = `agent-${snapshot.agent_id}`
        if (sourceId === targetId)
          return
        addEdge({
          id: `e-${sourceId}-${targetId}-${mapping.variable}`,
          source: sourceId,
          target: targetId,
          animated: true,
          label: mapping.variable,
          labelStyle: { fill: '#6b7280', fontSize: '11px', fontWeight: 500 },
          labelBgStyle: { fill: '#ffffff' },
          labelBgPadding: [4, 4] as [number, number],
          labelBgBorderRadius: 4,
        })
      }
    })
  })

  // 2. Edges based on execution order (sequential flow between order levels)
  const orderGroups = new Map<number, AgentExecutionSnapshot[]>()
  executions.forEach((snapshot) => {
    const order = snapshot.execution_order || 1
    if (!orderGroups.has(order)) {
      orderGroups.set(order, [])
    }
    orderGroups.get(order)!.push(snapshot)
  })
  const sortedOrders = [...orderGroups.keys()].sort((a, b) => a - b)
  for (let i = 0; i < sortedOrders.length - 1; i++) {
    const currentOrder = sortedOrders[i]
    const nextOrder = sortedOrders[i + 1]
    const currentGroup = orderGroups.get(currentOrder)!
    const nextGroup = orderGroups.get(nextOrder)!
    currentGroup.forEach((sourceSnapshot) => {
      nextGroup.forEach((targetSnapshot) => {
        const sourceId = `agent-${sourceSnapshot.agent_id}`
        const targetId = `agent-${targetSnapshot.agent_id}`
        if (sourceId === targetId)
          return
        addEdge({
          id: `e-order-${sourceId}-${targetId}`,
          source: sourceId,
          target: targetId,
          animated: true,
          type: 'smoothstep',
        })
      })
    })
  }

  edges.value = builtEdges

  nextTick(() => {
    fitView({ padding: 0.2 })
  })
}

watch(() => props.agentExecutions, (newExecutions) => {
  buildFlow(newExecutions)
}, { immediate: true, deep: true })
</script>

<template>
  <div class="flex flex-col h-[500px] border border-neutral-200 rounded-lg overflow-hidden bg-neutral-50">
    <!-- Header / Legend -->
    <div class="flex items-center justify-between px-4 py-3 border-b border-neutral-200 bg-white">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-git-branch" class="w-5 h-5 text-primary-500" />
        <h3 class="text-sm font-semibold text-neutral-900">
          Execution Flow
        </h3>
      </div>
      <div class="flex items-center gap-3 text-xs text-neutral-500">
        <div class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full bg-info-500" />
          <span>Dataset</span>
        </div>
        <div class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full bg-warning-500" />
          <span>Agent output</span>
        </div>
        <div class="flex items-center gap-1">
          <span class="w-2 h-2 rounded-full bg-success-500" />
          <span>Static</span>
        </div>
      </div>
    </div>

    <!-- Vue Flow Canvas -->
    <div class="flex-1 relative">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-zoom="1"
        :min-zoom="0.2"
        :max-zoom="4"
        :fit-view-on-init="true"
        :nodes-draggable="true"
        :nodes-connectable="false"
        :edges-updatable="false"
        :edges-focusable="false"
        :zoom-on-double-click="false"
      >
        <!-- Custom execution agent node type -->
        <template #node-execution-agent="nodeProps">
          <ExperimentsExecutionFlowNode v-bind="nodeProps" />
        </template>

        <!-- Background grid -->
        <VueFlowBackground pattern-color="#e5e7eb" :gap="20" />

        <!-- Controls (zoom, fit view, etc.) -->
        <VueFlowControls />

        <!-- Empty state overlay -->
        <div
          v-if="nodes.length === 0"
          class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
        >
          <UIcon name="i-lucide-git-branch" class="w-12 h-12 text-neutral-300 mb-4" />
          <p class="text-sm font-medium text-neutral-500 mb-1">
            No Agent Flow Available
          </p>
          <p class="text-xs text-neutral-400 text-center max-w-xs">
            This execution does not have any agent configuration snapshots to visualize.
          </p>
        </div>
      </VueFlow>
    </div>
  </div>
</template>

<style scoped>
:deep(.vue-flow) {
  height: 100%;
}
</style>
