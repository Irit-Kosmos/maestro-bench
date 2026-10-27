import type { Agent, AgentInputMapping, PromptVersion } from '~/types'
import type { GraphEdge } from '~/utils/graphLayout'
import { graphReaches } from '~/utils/graphLayout'

export interface AgentFlowNodeData {
  agent: Agent
  /** The step this node is: an agent that runs twice is two nodes */
  key: string
  /** The step's name: its agent's, then "name #2"… */
  label: string
  config?: Record<string, any>
}

/** A node has no position: the canvas lays the graph out itself */
export interface AgentFlowNode {
  id: string
  data: AgentFlowNodeData
}

export interface AgentFlowEdge extends GraphEdge {
  /** Variables of the target read from the source: the edge exists because of these mappings */
  variables?: string[]
  /** Created by a mapping, not drawn by hand: it goes when the mapping does */
  fromMapping?: boolean
}

export type InputMappingSource = 'dataset' | 'agent' | 'static'

const NODE_PREFIX = 'step-'

function nodeIdOf(key: string) {
  return `${NODE_PREFIX}${key}`
}

function keyOfNode(nodeId: string) {
  return nodeId.slice(NODE_PREFIX.length)
}

/**
 * State of the agent graph: which steps are on it and how they are connected.
 * An agent may be on the graph several times: configurations are by step key (see utils/steps).
 */
export function useAgentFlow(
  agents: Ref<readonly Agent[] | null | undefined>,
  agentConfigurations: Ref<Record<string, any>>,
  allPromptVersions: Ref<PromptVersion[] | null | undefined> = ref(null),
) {
  const nodes = ref<AgentFlowNode[]>([])
  const edges = ref<AgentFlowEdge[]>([])
  const selectedNodeId = ref<string | null>(null)

  // All the agents of the workspace
  const allAgents = computed(() => [...(agents.value ?? [])])

  // Keys of the steps currently in the flow
  const flowStepKeys = computed(() => nodes.value.map(n => n.data.key))

  function addNode(key: string, agent: Agent) {
    if (nodes.value.some(n => n.id === nodeIdOf(key)))
      return
    nodes.value.push({
      id: nodeIdOf(key),
      data: {
        agent,
        key,
        label: stepLabel(agent.name, splitStep(key).instance),
        config: agentConfigurations.value[key],
      },
    })
  }

  // Add a step of an agent to the flow canvas. The agent may already be there: it then runs again,
  // with a copy of the settings of its first step. Returns the key of the new step.
  function addAgentToFlow(agent: Agent): string {
    const key = stepKey(agent.id, nextInstance(agent.id, Object.keys(agentConfigurations.value)))
    const first = agentConfigurations.value[stepKey(agent.id)]
    if (first) {
      // Not in the run order until the graph gives it one
      const copy = JSON.parse(JSON.stringify(first))
      delete copy.execution_order
      agentConfigurations.value[key] = copy
    }
    else {
      agentConfigurations.value[key] = defaultAgentConfig(agent)
    }
    addNode(key, agent)
    return key
  }

  // Remove a step from the flow and drop its configuration.
  // Safe to call for a node that is already gone: the config cleanup must
  // still happen, otherwise the orphaned entry keeps blocking form validation.
  function removeAgentFromFlow(nodeId: string) {
    const key = keyOfNode(nodeId)

    // Remove edges connected to this node
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)

    // Remove node
    nodes.value = nodes.value.filter(n => n.id !== nodeId)

    // Clean up any references to this step from other steps' input mappings
    Object.keys(agentConfigurations.value).forEach((otherKey) => {
      if (otherKey === key)
        return
      const config = agentConfigurations.value[otherKey]
      if (config?.input_mappings) {
        config.input_mappings = config.input_mappings.filter(
          (m: AgentInputMapping) => m.source !== 'agent' || mappingSource(m) !== key,
        )
      }
    })

    // Clean up configuration
    delete agentConfigurations.value[key]

    // Clear selection
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = null
    }
  }

  // Update node data when configuration changes
  function updateNodeData(key: string) {
    const node = nodes.value.find(n => n.id === nodeIdOf(key))
    if (node?.data) {
      node.data = {
        ...node.data,
        config: { ...agentConfigurations.value[key] },
      }
    }
  }

  // Compute execution order from the flow graph using topological sort
  function computeExecutionOrder(): Map<string, number> {
    const order = new Map<string, number>()

    if (nodes.value.length === 0) {
      return order
    }

    // Build adjacency lists
    const incoming = new Map<string, Set<string>>()
    const outgoing = new Map<string, Set<string>>()

    nodes.value.forEach((node) => {
      incoming.set(node.id, new Set())
      outgoing.set(node.id, new Set())
    })

    edges.value.forEach((edge) => {
      if (incoming.has(edge.target)) {
        incoming.get(edge.target)!.add(edge.source)
      }
      if (outgoing.has(edge.source)) {
        outgoing.get(edge.source)!.add(edge.target)
      }
    })

    // Kahn's algorithm
    const queue: string[] = []
    const inDegree = new Map<string, number>()

    nodes.value.forEach((node) => {
      const degree = incoming.get(node.id)?.size || 0
      inDegree.set(node.id, degree)
      if (degree === 0) {
        queue.push(node.id)
      }
    })

    let currentOrder = 1
    const processed = new Set<string>()

    while (queue.length > 0) {
      const levelSize = queue.length

      for (let i = 0; i < levelSize; i++) {
        const nodeId = queue.shift()!
        if (processed.has(nodeId))
          continue

        order.set(keyOfNode(nodeId), currentOrder)
        processed.add(nodeId)

        const neighbors = outgoing.get(nodeId) || new Set()
        neighbors.forEach((neighborId) => {
          const newDegree = (inDegree.get(neighborId) || 0) - 1
          inDegree.set(neighborId, newDegree)
          if (newDegree === 0 && !processed.has(neighborId)) {
            queue.push(neighborId)
          }
        })
      }

      // Move to next order level
      if (queue.length > 0) {
        currentOrder++
      }
    }

    // Handle any disconnected nodes (no edges at all) - assign them the last order + 1
    // or if they have no edges but weren't reached, give them order 1
    nodes.value.forEach((node) => {
      const key = keyOfNode(node.id)
      if (!order.has(key)) {
        // Disconnected node - check if it has any edges
        const hasEdges = edges.value.some(e => e.source === node.id || e.target === node.id)
        if (!hasEdges) {
          // Truly isolated node - give it order 1 or last+1 depending on preference
          // For isolated nodes, we can treat them as parallel, so give them all the same order
          order.set(key, 1)
        }
        else {
          // Part of a cycle - give it a high order
          order.set(key, currentOrder + 1)
        }
      }
    })

    return order
  }

  // Remove input mappings for variables that are not in the current prompt
  function cleanupInputMappings(key: string) {
    if (!agentConfigurations.value[key])
      return
    const variables = getAgentPromptVariables(key)
    const mappings = getInputMappings(key)
    const cleaned = mappings.filter(m => variables.includes(m.variable))
    agentConfigurations.value[key].input_mappings = cleaned
  }

  // Update agent configuration and sync to node
  function updateAgentConfig(key: string, field: string, value: any) {
    if (!agentConfigurations.value[key]) {
      agentConfigurations.value[key] = {}
    }

    if (field === 'reset') {
      agentConfigurations.value[key] = value
    }
    else {
      agentConfigurations.value[key][field] = value
    }

    // Clean up stale input mappings when prompt version changes
    if (field === 'prompt_version_id') {
      cleanupInputMappings(key)
    }

    updateNodeData(key)
  }

  // Parse prompt version variables from JSON string to array
  function parsePromptVariables(variablesJson: string | null | undefined): string[] {
    if (!variablesJson)
      return []
    try {
      const parsed = JSON.parse(variablesJson)
      if (Array.isArray(parsed))
        return parsed
      if (typeof parsed === 'object' && parsed !== null)
        return Object.keys(parsed)
      return []
    }
    catch {
      return []
    }
  }

  // Get the variables required by an agent's selected prompt version
  function getAgentPromptVariables(key: string): string[] {
    const config = agentConfigurations.value[key]
    if (!config?.prompt_version_id)
      return []
    const version = allPromptVersions.value?.find(v => v.id === config.prompt_version_id)
    return parsePromptVariables(version?.variables)
  }

  // Get input mappings for an agent
  function getInputMappings(key: string): AgentInputMapping[] {
    return agentConfigurations.value[key]?.input_mappings || []
  }

  // Find mapping for a specific variable
  function getVariableMapping(key: string, variable: string): AgentInputMapping | undefined {
    return getInputMappings(key).find(m => m.variable === variable)
  }

  // Check if a variable has a mapping
  function isVariableMapped(key: string, variable: string): boolean {
    return getVariableMapping(key, variable) !== undefined
  }

  // Update or add an input mapping for a variable
  function updateInputMapping(key: string, mapping: AgentInputMapping) {
    if (!agentConfigurations.value[key])
      return
    const mappings = getInputMappings(key)
    const index = mappings.findIndex(m => m.variable === mapping.variable)
    if (index > -1) {
      mappings[index] = mapping
    }
    else {
      mappings.push(mapping)
    }
    agentConfigurations.value[key].input_mappings = mappings
    updateNodeData(key)
  }

  // Remove an input mapping for a variable
  function removeInputMapping(key: string, variable: string) {
    if (!agentConfigurations.value[key])
      return
    const mappings = getInputMappings(key).filter(m => m.variable !== variable)
    agentConfigurations.value[key].input_mappings = mappings
    updateNodeData(key)
  }

  // Variables a step actually reads: an aggregator keeps the mappings of variables it no longer uses
  function usedVariables(key: string, agent: Agent): string[] {
    if (agent.kind === 'aggregator')
      return formulaVariables(agentConfigurations.value[key]?.formulas)
    return getAgentPromptVariables(key)
  }

  // An agent reading another one's output depends on it: that is an edge, labelled with the variables
  // it carries. Such an edge also orders the run, and stays until the mapping goes.
  function syncMappingEdges() {
    const wanted = new Map<string, { source: string, target: string, variables: string[] }>()
    for (const node of nodes.value) {
      const agent = node.data?.agent
      if (!agent)
        continue
      const used = usedVariables(node.data.key, agent)
      for (const mapping of getInputMappings(node.data.key)) {
        const sourceStep = mappingSource(mapping)
        if (mapping.source !== 'agent' || sourceStep === undefined || !used.includes(mapping.variable))
          continue
        const source = nodeIdOf(sourceStep)
        if (source === node.id || !nodes.value.some(n => n.id === source))
          continue
        const id = `e-${source}-${node.id}`
        const entry = wanted.get(id) ?? { source, target: node.id, variables: [] }
        entry.variables.push(mapping.variable)
        wanted.set(id, entry)
      }
    }

    const next: AgentFlowEdge[] = []
    for (const edge of edges.value) {
      const carried = wanted.get(edge.id)
      if (carried) {
        next.push(mappingEdge(edge, carried.variables))
        wanted.delete(edge.id)
      }
      else if (edge.fromMapping) {
        // Drawn for a mapping that is gone
        continue
      }
      else if (edge.variables) {
        // Drawn by hand, and no longer carries anything: plain order edge again
        next.push({ id: edge.id, source: edge.source, target: edge.target })
      }
      else {
        next.push(edge)
      }
    }
    for (const [id, { source, target, variables }] of wanted)
      next.push(mappingEdge({ id, source, target, fromMapping: true }, variables))

    if (JSON.stringify(next.map(edgeKey)) !== JSON.stringify(edges.value.map(edgeKey)))
      edges.value = next
  }

  function mappingEdge(edge: AgentFlowEdge, variables: string[]): AgentFlowEdge {
    return {
      ...edge,
      // Removing it would leave the mapping without its source: change the mapping instead
      deletable: false,
      label: variables.join(', '),
      variables,
    }
  }

  function edgeKey(edge: AgentFlowEdge) {
    return [edge.id, edge.label ?? '', edge.fromMapping ?? false]
  }

  // Whether `source` may feed `target`: not itself, not twice, and never in a loop
  function canConnect(source: string, target: string): boolean {
    if (source === target || edges.value.some(e => e.source === source && e.target === target))
      return false
    return !graphReaches(edges.value, target, source)
  }

  function connect(source: string, target: string) {
    if (!canConnect(source, target))
      return
    edges.value.push({ id: `e-${source}-${target}`, source, target })
  }

  function disconnect(edgeId: string) {
    const edge = edges.value.find(e => e.id === edgeId)
    // An edge carrying variables stays as long as their mappings do
    if (edge && !edge.variables?.length)
      edges.value = edges.value.filter(e => e.id !== edgeId)
  }

  // Sync flow nodes from existing step configurations.
  // Steps are chained in run order, so the graph opens as the same sequence the list showed.
  function syncFromConfigs() {
    // Only sync if canvas is empty (preserve existing layout)
    if (nodes.value.length > 0)
      return

    const ordered = Object.keys(agentConfigurations.value)
      .map(key => ({ key, agent: allAgents.value.find(a => a.id === agentIdOfStep(key)) }))
      .filter((step): step is { key: string, agent: Agent } => !!step.agent)
      .sort((a, b) =>
        (agentConfigurations.value[a.key]?.execution_order ?? Number.POSITIVE_INFINITY)
        - (agentConfigurations.value[b.key]?.execution_order ?? Number.POSITIVE_INFINITY)
        || a.agent.id - b.agent.id
        || splitStep(a.key).instance - splitStep(b.key).instance)

    ordered.forEach((step, index) => {
      addNode(step.key, step.agent)
      if (index > 0)
        connect(nodeIdOf(ordered[index - 1]!.key), nodeIdOf(step.key))
    })
    syncMappingEdges()
  }

  return {
    // State
    nodes,
    edges,
    selectedNodeId,

    // Computed
    allAgents,
    flowStepKeys,

    // Methods
    nodeIdOf,
    keyOfNode,
    addAgentToFlow,
    removeAgentFromFlow,
    computeExecutionOrder,
    updateAgentConfig,
    syncFromConfigs,
    syncMappingEdges,
    canConnect,
    connect,
    disconnect,

    // Input mapping helpers
    parsePromptVariables,
    getAgentPromptVariables,
    getInputMappings,
    getVariableMapping,
    isVariableMapped,
    updateInputMapping,
    removeInputMapping,
  }
}
