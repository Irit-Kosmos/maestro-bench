<script setup lang="ts">
import type { StepRef } from '~/composables/useAgentPipeline'
import type { Agent, Model, PromptVersion } from '~/types'
import { useAgentFlow } from '~/composables/useAgentFlow'

interface Props {
  agents?: Agent[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  agentConfigurations: Record<string, any>
  datasetHeaders?: readonly string[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  updateAgentConfig: [stepKey: string, field: string, value: any]
  removeAgentConfig: [stepKey: string]
  addAgent: [stepKey: string]
  openPromptDetails: [promptVersionId: number]
}>()

defineSlots<{
  tools?: (props: { settled: boolean }) => any
}>()

// Provide models and prompt versions for child nodes to resolve names
provide('agentFlowModels', computed(() => props.models || []))
provide('agentFlowPromptVersions', computed(() => props.allPromptVersions || []))

// Initialize agent flow state
const flow = useAgentFlow(
  computed(() => props.agents || []),
  toRef(props, 'agentConfigurations'),
  computed(() => props.allPromptVersions || []),
)

const {
  nodes,
  edges,
  selectedNodeId,
  allAgents,
  flowStepKeys,
  nodeIdOf,
  keyOfNode,
  addAgentToFlow,
  removeAgentFromFlow,
  computeExecutionOrder,
  updateAgentConfig: flowUpdateAgentConfig,
  syncFromConfigs,
  syncMappingEdges,
  updateInputMapping,
  getInputMappings,
  canConnect,
  connect,
  disconnect,
} = flow

// Step of each agent: the nodes show it, so the run order reads off the graph
provide('agentFlowOrder', computed(() => computeExecutionOrder()))

// Auto-populate the canvas from the agent configurations, also when they change under it
// (e.g. switching from the list view)
watch(() => props.agentConfigurations, () => {
  if (nodes.value.length === 0) {
    syncFromConfigs()
  }
  syncMappingEdges()
}, { immediate: true, deep: true })

// A node added or removed can start or stop carrying a mapping
watch(() => nodes.value.length, () => syncMappingEdges())

// Agents the "+" under a node offers: all of them, an agent may run again
provide('agentFlowAvailable', allAgents)

const canvasEdges = computed(() => edges.value.map((edge) => {
  const name = (id: string) => nodes.value.find(n => n.id === id)?.data.label
  return {
    ...edge,
    name: `${name(edge.source) ?? ''} to ${name(edge.target) ?? ''}`,
    // An edge that carries nothing is only an order: cutting it lets the two agents run side by side
    removeLabel: 'Run in parallel: remove this dependency',
  }
}))

// Selected node data for config panel
const selectedNode = computed(() => {
  if (!selectedNodeId.value)
    return null
  return nodes.value.find(n => n.id === selectedNodeId.value)?.data ?? null
})

const selectedAgent = computed<Agent | null>(() => selectedNode.value?.agent ?? null)

const selectedConfig = computed(() => {
  if (!selectedNode.value)
    return undefined
  return props.agentConfigurations[selectedNode.value.key]
})

// w-80: the panel lies over the canvas, which keeps the graph clear of it
const PANEL_WIDTH = 320

// Add an agent from the picker above the graph, or from the "+" under a node, which also connects it
function handleAddAgent(agent: Agent, after?: string) {
  const key = addAgentToFlow(agent)
  if (after)
    connect(after, nodeIdOf(key))
  emit('addAgent', key)
}
provide('agentFlowAddAfter', (after: string, agent: Agent) => handleAddAgent(agent, after))

// Remove a node and drop its configuration
function removeNode(nodeId: string) {
  const key = keyOfNode(nodeId)
  removeAgentFromFlow(nodeId)
  // Remove the config entry entirely — reusing 'reset' with undefined would
  // resurrect the key pointing at undefined, which then falsely counts as an
  // active agent in form validation.
  emit('removeAgentConfig', key)
}

// Handle config panel updates
function handleUpdateConfig(field: string, value: any) {
  if (!selectedNode.value)
    return
  flowUpdateAgentConfig(selectedNode.value.key, field, value)
  emit('updateAgentConfig', selectedNode.value.key, field, value)
}

// Handle reset
function handleResetAgent() {
  if (!selectedNode.value)
    return
  const { agent, key } = selectedNode.value
  const resetValue = {
    ...defaultAgentConfig(agent),
    execution_order: props.agentConfigurations[key]?.execution_order,
  }
  flowUpdateAgentConfig(key, 'reset', resetValue)
  emit('updateAgentConfig', key, 'reset', resetValue)
}

// Handle input mapping updates from config panel
function handleUpdateInputMapping(mapping: any) {
  if (!selectedNode.value)
    return
  const { key } = selectedNode.value
  updateInputMapping(key, mapping)
  emit('updateAgentConfig', key, 'input_mappings', getInputMappings(key))
}

// Steps the selected one may read: every other step of the flow except those that run after it
// (reading one of them would make a cycle). Mapping a variable to one draws the edge, so the source
// does not have to be connected first. Ordered by run order, nearest last.
const upstreamSteps = computed<StepRef[]>(() => {
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
    .map(n => n.data)
    .filter(data => !!data?.agent)
    .map(data => ({ key: data.key, label: data.label, agent: data.agent }))
    .sort((a, b) => (order.get(a.key) ?? 0) - (order.get(b.key) ?? 0))
})

// Expose computeExecutionOrder for parent to call
defineExpose({
  computeExecutionOrder,
  addAgent: (agent: Agent) => handleAddAgent(agent),
  getFlowStepKeys: () => flowStepKeys.value,
})
</script>

<template>
  <GraphFrame height="clamp(520px, 72dvh, 820px)" label="Agent graph">
    <template #default="{ expanded, settled, toggle }">
      <div class="relative size-full">
        <GraphCanvas
          :nodes="nodes"
          :edges="canvasEdges"
          :selected="selectedNodeId"
          :inset-right="selectedAgent ? PANEL_WIDTH : 0"
          :can-connect="canConnect"
          :label-of="node => node.data.label"
          :scroll-pans="expanded"
          label="Agent graph"
          interactive
          @select="id => selectedNodeId = id"
          @connect="connect"
          @disconnect="disconnect"
          @remove="removeNode"
        >
          <template #node="{ node, selected, leaf }">
            <ExperimentsAgentFlowNode :id="node.id" :data="node.data" :selected="selected" :leaf="leaf" />
          </template>

          <!-- Full screen covers the picker above the graph: it comes along, over the canvas -->
          <template #tools>
            <slot name="tools" :settled="settled" />
          </template>

          <template #actions>
            <GraphControl
              :label="expanded ? 'Exit full screen' : 'Full screen'"
              :icon="expanded ? 'i-ph-arrows-in-simple-bold' : 'i-ph-arrows-out-simple-bold'"
              :kbd="expanded ? 'Esc' : undefined"
              @click="toggle"
            />
          </template>

          <template #empty>
            <div class="flex max-w-xs flex-col items-center px-4 text-center">
              <UIcon name="i-ph-git-branch-bold" class="mb-3 size-8 text-dimmed" aria-hidden="true" />
              <p class="mb-1 text-sm font-medium text-muted">
                Build your agent flow
              </p>
              <p class="text-xs text-muted">
                Add agents above, then use the “+” under an agent to pick the one that runs after it. You can also drag from that “+” to another agent.
              </p>
            </div>
          </template>
        </GraphCanvas>

        <!-- The panel lies over the graph rather than beside it: the graph keeps its size, and pans clear of the panel -->
        <Transition
          enter-active-class="transition-[opacity,transform] duration-200 ease-out motion-reduce:transition-none"
          enter-from-class="opacity-0 translate-x-full"
          enter-to-class="opacity-100 translate-x-0"
          leave-active-class="transition-[opacity,transform] duration-150 ease-out motion-reduce:transition-none"
          leave-from-class="opacity-100 translate-x-0"
          leave-to-class="opacity-0 translate-x-full"
        >
          <div v-if="selectedAgent" class="absolute inset-y-0 right-0 z-20 max-w-full shadow-lg">
            <ExperimentsAgentConfigPanel
              :agent="selectedAgent"
              :label="selectedNode?.label"
              :config="selectedConfig"
              :models="models || []"
              :all-prompt-versions="allPromptVersions || []"
              :dataset-headers="datasetHeaders || []"
              :upstream-steps="upstreamSteps"
              @update-config="handleUpdateConfig"
              @update-input-mapping="handleUpdateInputMapping"
              @remove="removeNode(selectedNodeId!)"
              @close="selectedNodeId = null"
              @reset="handleResetAgent"
              @open-prompt-details="id => emit('openPromptDetails', id)"
            />
          </div>
        </Transition>
      </div>
    </template>
  </GraphFrame>
</template>
