import type { Edge, Node } from '@vue-flow/core'
import type { Agent, AgentInputMapping, AgentTeam, PromptVersion } from '~/types'

export interface AgentFlowNodeData {
  agent: Agent
  team?: AgentTeam
  config?: Record<string, any>
}

export type InputMappingSource = 'dataset' | 'agent' | 'static'

/**
 * Composable for managing the Vue Flow agent graph state
 */
export function useAgentFlow(
  agentTeams: Ref<AgentTeam[] | null | undefined>,
  agentConfigurations: Ref<Record<number, any>>,
  allPromptVersions: Ref<PromptVersion[] | null | undefined> = ref(null),
) {
  // Cast avoids TS "excessively deep" instantiation on Vue Flow's Node type
  const nodes = ref([]) as Ref<Node<AgentFlowNodeData>[]>
  const edges = ref([]) as Ref<Edge[]>
  const selectedNodeId = ref<string | null>(null)

  // Get all available agents grouped by team
  const allAgentsByTeam = computed(() => {
    const result: { team: AgentTeam, agents: Agent[] }[] = []
    agentTeams.value?.forEach((team) => {
      if (team.agents && team.agents.length > 0) {
        result.push({ team, agents: [...team.agents] })
      }
    })
    return result
  })

  // Get a flat list of all agents
  const allAgents = computed(() => {
    const agents: Agent[] = []
    allAgentsByTeam.value.forEach(({ agents: teamAgents }) => {
      agents.push(...teamAgents)
    })
    return agents
  })

  // Get all agent IDs currently in the flow
  const flowAgentIds = computed(() => {
    return nodes.value.map(n => Number.parseInt(n.id.replace('agent-', '')))
  })

  // Check if an agent is already in the flow
  function isAgentInFlow(agentId: number): boolean {
    return nodes.value.some(n => n.id === `agent-${agentId}`)
  }

  // Find a team by agent
  function getTeamForAgent(agentId: number): AgentTeam | undefined {
    return agentTeams.value?.find(t => t.agents?.some(a => a.id === agentId))
  }

  // Add an agent to the flow canvas
  function addAgentToFlow(agent: Agent, position?: { x: number, y: number }) {
    const nodeId = `agent-${agent.id}`

    if (isAgentInFlow(agent.id)) {
      return
    }

    // Initialize agent configuration with defaults
    if (!agentConfigurations.value[agent.id]) {
      agentConfigurations.value[agent.id] = defaultAgentConfig(agent)
    }

    const team = getTeamForAgent(agent.id)

    // Determine position - if not provided, auto-layout horizontally
    const xPos = position?.x ?? 50 + (nodes.value.length * 250)
    const yPos = position?.y ?? 100 + (nodes.value.length % 3) * 120

    nodes.value.push({
      id: nodeId,
      type: 'agent',
      position: { x: xPos, y: yPos },
      data: {
        agent,
        team,
        config: agentConfigurations.value[agent.id],
      },
    })
  }

  // Remove an agent from the flow and drop its configuration.
  // Safe to call when the node has already been removed from the canvas
  // (e.g. by Vue Flow's Delete/Backspace shortcut): the config cleanup must
  // still happen, otherwise the orphaned entry keeps blocking form validation.
  function removeAgentFromFlow(nodeId: string) {
    const agentId = Number.parseInt(nodeId.replace('agent-', ''))

    // Remove edges connected to this node
    edges.value = edges.value.filter(e => e.source !== nodeId && e.target !== nodeId)

    // Remove node
    nodes.value = nodes.value.filter(n => n.id !== nodeId)

    // Clean up any references to this agent from other agents' input mappings
    Object.keys(agentConfigurations.value).forEach((key) => {
      const otherAgentId = Number.parseInt(key)
      if (otherAgentId === agentId)
        return
      const config = agentConfigurations.value[otherAgentId]
      if (config?.input_mappings) {
        config.input_mappings = config.input_mappings.filter(
          (m: AgentInputMapping) => m.source !== 'agent' || m.sourceAgentId !== agentId,
        )
      }
    })

    // Clean up configuration
    delete agentConfigurations.value[agentId]

    // Clear selection
    if (selectedNodeId.value === nodeId) {
      selectedNodeId.value = null
    }
  }

  // Update node data when configuration changes
  function updateNodeData(agentId: number) {
    const nodeId = `agent-${agentId}`
    const node = nodes.value.find(n => n.id === nodeId)
    if (node?.data) {
      node.data = {
        ...node.data,
        config: { ...agentConfigurations.value[agentId] },
      }
    }
  }

  // Compute execution order from the flow graph using topological sort
  function computeExecutionOrder(): Map<number, number> {
    const order = new Map<number, number>()

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

        const agentId = Number.parseInt(nodeId.replace('agent-', ''))
        order.set(agentId, currentOrder)
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
      const agentId = Number.parseInt(node.id.replace('agent-', ''))
      if (!order.has(agentId)) {
        // Disconnected node - check if it has any edges
        const hasEdges = edges.value.some(e => e.source === node.id || e.target === node.id)
        if (!hasEdges) {
          // Truly isolated node - give it order 1 or last+1 depending on preference
          // For isolated nodes, we can treat them as parallel, so give them all the same order
          order.set(agentId, 1)
        }
        else {
          // Part of a cycle - give it a high order
          order.set(agentId, currentOrder + 1)
        }
      }
    })

    return order
  }

  // Get unique team IDs from all agents in the flow
  function getFlowTeamIds(): number[] {
    const teamIds = new Set<number>()
    nodes.value.forEach((node) => {
      const agent = node.data?.agent
      if (agent?.team_id) {
        teamIds.add(agent.team_id)
      }
    })
    return Array.from(teamIds)
  }

  // Remove input mappings for variables that are not in the current prompt
  function cleanupInputMappings(agentId: number) {
    if (!agentConfigurations.value[agentId])
      return
    const variables = getAgentPromptVariables(agentId)
    const mappings = getInputMappings(agentId)
    const cleaned = mappings.filter(m => variables.includes(m.variable))
    agentConfigurations.value[agentId].input_mappings = cleaned
  }

  // Update agent configuration and sync to node
  function updateAgentConfig(agentId: number, field: string, value: any) {
    if (!agentConfigurations.value[agentId]) {
      agentConfigurations.value[agentId] = {}
    }

    if (field === 'reset') {
      agentConfigurations.value[agentId] = value
    }
    else {
      agentConfigurations.value[agentId][field] = value
    }

    // Clean up stale input mappings when prompt version changes
    if (field === 'prompt_version_id') {
      cleanupInputMappings(agentId)
    }

    updateNodeData(agentId)
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
  function getAgentPromptVariables(agentId: number): string[] {
    const config = agentConfigurations.value[agentId]
    if (!config?.prompt_version_id)
      return []
    const version = allPromptVersions.value?.find(v => v.id === config.prompt_version_id)
    return parsePromptVariables(version?.variables)
  }

  // Get input mappings for an agent
  function getInputMappings(agentId: number): AgentInputMapping[] {
    return agentConfigurations.value[agentId]?.input_mappings || []
  }

  // Find mapping for a specific variable
  function getVariableMapping(agentId: number, variable: string): AgentInputMapping | undefined {
    return getInputMappings(agentId).find(m => m.variable === variable)
  }

  // Check if a variable has a mapping
  function isVariableMapped(agentId: number, variable: string): boolean {
    return getVariableMapping(agentId, variable) !== undefined
  }

  // Update or add an input mapping for a variable
  function updateInputMapping(agentId: number, mapping: AgentInputMapping) {
    if (!agentConfigurations.value[agentId])
      return
    const mappings = getInputMappings(agentId)
    const index = mappings.findIndex(m => m.variable === mapping.variable)
    if (index > -1) {
      mappings[index] = mapping
    }
    else {
      mappings.push(mapping)
    }
    agentConfigurations.value[agentId].input_mappings = mappings
    updateNodeData(agentId)
  }

  // Remove an input mapping for a variable
  function removeInputMapping(agentId: number, variable: string) {
    if (!agentConfigurations.value[agentId])
      return
    const mappings = getInputMappings(agentId).filter(m => m.variable !== variable)
    agentConfigurations.value[agentId].input_mappings = mappings
    updateNodeData(agentId)
  }

  // Variables an agent actually reads: an aggregator keeps the mappings of variables it no longer uses
  function usedVariables(agent: Agent): string[] {
    if (agent.kind === 'aggregator')
      return formulaVariables(agentConfigurations.value[agent.id]?.formulas)
    return getAgentPromptVariables(agent.id)
  }

  // An agent reading another one's output depends on it: that is an edge, labelled with the variables
  // it carries. Such an edge also orders the run, and stays until the mapping goes.
  function syncMappingEdges() {
    const wanted = new Map<string, { source: string, target: string, variables: string[] }>()
    for (const node of nodes.value) {
      const agent = node.data?.agent
      if (!agent)
        continue
      const used = usedVariables(agent)
      for (const mapping of getInputMappings(agent.id)) {
        if (mapping.source !== 'agent' || mapping.sourceAgentId === undefined || !used.includes(mapping.variable))
          continue
        const source = `agent-${mapping.sourceAgentId}`
        if (source === node.id || !nodes.value.some(n => n.id === source))
          continue
        const id = `e-${source}-${node.id}`
        const entry = wanted.get(id) ?? { source, target: node.id, variables: [] }
        entry.variables.push(mapping.variable)
        wanted.set(id, entry)
      }
    }

    const next: Edge[] = []
    for (const edge of edges.value) {
      const carried = wanted.get(edge.id)
      if (carried) {
        next.push(mappingEdge(edge, carried.variables))
        wanted.delete(edge.id)
      }
      else if (edge.data?.fromMapping) {
        // Drawn for a mapping that is gone
        continue
      }
      else if (edge.data?.variables) {
        // Drawn by hand, and no longer carries anything: plain order edge again
        next.push({ id: edge.id, source: edge.source, target: edge.target, animated: true })
      }
      else {
        next.push(edge)
      }
    }
    for (const [id, { source, target, variables }] of wanted)
      next.push(mappingEdge({ id, source, target, data: { fromMapping: true } }, variables))

    if (JSON.stringify(next.map(edgeKey)) !== JSON.stringify(edges.value.map(edgeKey)))
      edges.value = next
  }

  function mappingEdge(edge: Edge, variables: string[]): Edge {
    return {
      ...edge,
      animated: true,
      // Removing it would leave the mapping without its source: change the mapping instead
      deletable: false,
      label: variables.join(', '),
      labelStyle: { fill: 'var(--ui-text-muted)', fontSize: '11px', fontFamily: 'var(--font-mono, ui-monospace, monospace)' },
      labelBgStyle: { fill: 'var(--ui-bg)' },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 4,
      data: { ...edge.data, variables },
    }
  }

  function edgeKey(edge: Edge) {
    return [edge.id, edge.label ?? '', edge.data?.fromMapping ?? false]
  }

  // Sync flow nodes from existing agent configurations.
  // Agents are laid out left to right in run order and chained, so the graph opens
  // as the same sequence the list showed.
  function syncFromConfigs() {
    // Only sync if canvas is empty (preserve existing layout)
    if (nodes.value.length > 0)
      return

    const ordered = Object.keys(agentConfigurations.value)
      .map(key => allAgents.value.find(a => a.id === Number.parseInt(key)))
      .filter((agent): agent is Agent => !!agent)
      .sort((a, b) =>
        (agentConfigurations.value[a.id]?.execution_order ?? Number.POSITIVE_INFINITY)
        - (agentConfigurations.value[b.id]?.execution_order ?? Number.POSITIVE_INFINITY)
        || a.id - b.id)

    ordered.forEach((agent, index) => {
      addAgentToFlow(agent, { x: 50 + index * 260, y: 100 })
      if (index > 0) {
        const source = `agent-${ordered[index - 1]!.id}`
        const target = `agent-${agent.id}`
        edges.value.push({ id: `e-${source}-${target}`, source, target, animated: true })
      }
    })
    syncMappingEdges()
  }

  return {
    // State
    nodes,
    edges,
    selectedNodeId,

    // Computed
    allAgentsByTeam,
    allAgents,
    flowAgentIds,

    // Methods
    isAgentInFlow,
    addAgentToFlow,
    removeAgentFromFlow,
    computeExecutionOrder,
    getFlowTeamIds,
    updateAgentConfig,
    syncFromConfigs,
    syncMappingEdges,

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
