<script setup lang="ts">
import type { Agent, AgentTeam, Model, PromptVersion } from '~/types'
import { useVueFlow } from '@vue-flow/core'
import { useAgentFlow } from '~/composables/useAgentFlow'

interface Props {
  agentTeams?: AgentTeam[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  agentConfigurations: Record<number, any>
  datasetHeaders?: readonly string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  updateAgentConfig: [agentId: number, field: string, value: any]
  removeAgentConfig: [agentId: number]
  addAgent: [agentId: number]
  openPromptDetails: [promptVersionId: number]
}>()

// Provide models and prompt versions for child nodes to resolve names
provide('agentFlowModels', computed(() => props.models || []))
provide('agentFlowPromptVersions', computed(() => props.allPromptVersions || []))

// The node a click just added: it eases in, while the ones restored with the flow are simply there
const enteringNodeId = ref<string | null>(null)
provide('agentFlowEnteringNode', enteringNodeId)

// Initialize agent flow state
const flow = useAgentFlow(
  computed(() => props.agentTeams || []),
  toRef(props, 'agentConfigurations'),
  computed(() => props.allPromptVersions || []),
)

const {
  nodes,
  edges,
  selectedNodeId,
  allAgentsByTeam,
  flowAgentIds,
  addAgentToFlow,
  removeAgentFromFlow,
  computeExecutionOrder,
  updateAgentConfig: flowUpdateAgentConfig,
  syncFromConfigs,
  syncMappingEdges,
  updateInputMapping,
  getInputMappings,
} = flow

// Vue Flow instance
const { fitView, onInit, onNodesChange } = useVueFlow()

onInit(() => {
  // Auto-populate canvas from existing agent configurations
  syncFromConfigs()
  fitView()
})

// Nodes removed by Vue Flow itself (Delete/Backspace on a selected node) must
// also drop their configuration, otherwise the form keeps waiting for an agent
// that is no longer on the canvas.
onNodesChange((changes) => {
  changes.forEach((change) => {
    if (change.type !== 'remove')
      return
    const agentId = Number.parseInt(change.id.replace('agent-', ''))
    removeAgentFromFlow(change.id)
    emit('removeAgentConfig', agentId)
  })
})

// Also sync when agentConfigurations changes (e.g., switching from card view)
watch(() => props.agentConfigurations, () => {
  if (nodes.value.length === 0) {
    syncFromConfigs()
  }
  syncMappingEdges()
}, { immediate: true, deep: true })

// A node added or removed can start or stop carrying a mapping
watch(() => nodes.value.length, () => syncMappingEdges())

// Selected node data for config panel
const selectedAgent = computed<Agent | null>(() => {
  if (!selectedNodeId.value)
    return null
  const node = nodes.value.find(n => n.id === selectedNodeId.value)
  return node?.data?.agent || null
})

const selectedConfig = computed(() => {
  if (!selectedNodeId.value || !selectedAgent.value)
    return undefined
  return props.agentConfigurations[selectedAgent.value.id]
})

// Handle node click
function onNodeClick(event: any) {
  selectedNodeId.value = event.node.id
}

// Handle canvas click (deselect)
function onPaneClick() {
  selectedNodeId.value = null
}

// Handle edge connect
function onConnect(connection: any) {
  edges.value.push({
    id: `e-${connection.source}-${connection.target}`,
    source: connection.source,
    target: connection.target,
    animated: true,
  })
}

// Handle edge click to delete
function onEdgeClick(event: any) {
  // An edge carrying variables stays as long as their mappings do
  if (event.edge.data?.variables?.length)
    return
  const edgeId = event.edge.id
  edges.value = edges.value.filter(e => e.id !== edgeId)
}

// Add agent from palette
function handleAddAgent(agent: Agent) {
  enteringNodeId.value = `agent-${agent.id}`
  addAgentToFlow(agent)
  emit('addAgent', agent.id)
  nextTick(() => {
    fitView({ padding: 0.2 })
  })
}

// Handle config panel updates
function handleUpdateConfig(field: string, value: any) {
  if (!selectedAgent.value)
    return
  flowUpdateAgentConfig(selectedAgent.value.id, field, value)
  emit('updateAgentConfig', selectedAgent.value.id, field, value)
}

// Handle config panel remove
function handleRemoveAgent() {
  if (!selectedNodeId.value)
    return
  const nodeId = selectedNodeId.value
  const agentId = Number.parseInt(nodeId.replace('agent-', ''))
  removeAgentFromFlow(nodeId)
  // Remove the config entry entirely — reusing 'reset' with undefined would
  // resurrect the key pointing at undefined, which then falsely counts as an
  // active agent in form validation.
  emit('removeAgentConfig', agentId)
}

// Handle reset
function handleResetAgent() {
  if (!selectedAgent.value)
    return
  const agent = selectedAgent.value
  const resetValue = {
    ...defaultAgentConfig(agent),
    execution_order: props.agentConfigurations[agent.id]?.execution_order,
  }
  flowUpdateAgentConfig(agent.id, 'reset', resetValue)
  emit('updateAgentConfig', agent.id, 'reset', resetValue)
}

// Handle open prompt details
function handleOpenPromptDetails(promptVersionId: number) {
  emit('openPromptDetails', promptVersionId)
}

// Handle input mapping updates from config panel
function handleUpdateInputMapping(mapping: any) {
  if (!selectedAgent.value)
    return
  updateInputMapping(selectedAgent.value.id, mapping)
  emit('updateAgentConfig', selectedAgent.value.id, 'input_mappings', getInputMappings(selectedAgent.value.id))
}

// Agents the selected one may read: every other agent of the flow except those that run after it
// (reading one of them would make a cycle). Mapping a variable to one draws the edge, so the source
// does not have to be connected first. Ordered by run order, nearest last.
const upstreamAgents = computed<Agent[]>(() => {
  if (!selectedNodeId.value)
    return []
  const downstream = new Set<string>([selectedNodeId.value])
  const queue = [selectedNodeId.value]
  while (queue.length > 0) {
    const current = queue.shift()!
    edges.value
      .filter(e => e.source === current && !downstream.has(e.target))
      .forEach((e) => {
        downstream.add(e.target)
        queue.push(e.target)
      })
  }
  const order = computeExecutionOrder()
  return nodes.value
    .filter(n => !downstream.has(n.id))
    .map(n => n.data?.agent)
    .filter((agent): agent is Agent => !!agent)
    .sort((a, b) => (order.get(a.id) ?? 0) - (order.get(b.id) ?? 0))
})

// Expose computeExecutionOrder for parent to call
defineExpose({
  computeExecutionOrder,
  getFlowTeamIds: flow.getFlowTeamIds,
  getFlowAgentIds: () => flowAgentIds.value,
})
</script>

<template>
  <div class="flex h-[500px] border border-default rounded-lg overflow-hidden bg-muted">
    <!-- Agent Palette Sidebar -->
    <ExperimentsAgentPalette
      :agent-teams="allAgentsByTeam.map(g => g.team)"
      :flow-agent-ids="flowAgentIds"
      @add-agent="handleAddAgent"
    />

    <!-- Vue Flow Canvas -->
    <div class="flex-1 relative">
      <VueFlow
        v-model:nodes="nodes"
        v-model:edges="edges"
        :default-zoom="1"
        :min-zoom="0.2"
        :max-zoom="4"
        :fit-view-on-init="true"
        @node-click="onNodeClick"
        @pane-click="onPaneClick"
        @connect="onConnect"
        @edge-click="onEdgeClick"
      >
        <!-- Custom agent node type -->
        <template #node-agent="nodeProps">
          <ExperimentsAgentFlowNode v-bind="nodeProps" />
        </template>

        <!-- Background grid -->
        <VueFlowBackground pattern-color="var(--ui-border)" :gap="20" />

        <!-- Controls (zoom, fit view, etc.) -->
        <VueFlowControls />

        <!-- Empty state overlay -->
        <Transition leave-active-class="transition-opacity duration-150 ease-out" leave-to-class="opacity-0">
          <div
            v-if="nodes.length === 0"
            class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
          >
            <UIcon name="i-ph-git-branch-bold" class="w-12 h-12 text-dimmed mb-4" />
            <p class="text-sm font-medium text-muted mb-1">
              Build Your Agent Flow
            </p>
            <p class="text-xs text-dimmed text-center max-w-xs">
              Click agents from the sidebar to add them to the canvas. Connect them with edges to define execution order.
            </p>
          </div>
        </Transition>
      </VueFlow>
    </div>

    <!-- Config Panel (slides in from right) -->
    <Transition
      enter-active-class="transition-transform transition-opacity duration-200 ease-out"
      enter-from-class="opacity-0 translate-x-full"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition-transform transition-opacity duration-150 ease-out"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-full"
    >
      <ExperimentsAgentConfigPanel
        v-if="selectedAgent"
        :agent="selectedAgent"
        :config="selectedConfig"
        :models="models || []"
        :all-prompt-versions="allPromptVersions || []"
        :dataset-headers="datasetHeaders || []"
        :upstream-agents="upstreamAgents"
        @update-config="handleUpdateConfig"
        @update-input-mapping="handleUpdateInputMapping"
        @remove="handleRemoveAgent"
        @close="selectedNodeId = null"
        @reset="handleResetAgent"
        @open-prompt-details="handleOpenPromptDetails"
      />
    </Transition>
  </div>
</template>

<style scoped>
/* Ensure Vue Flow takes full height */
:deep(.vue-flow) {
  height: 100%;
}
</style>
