import type { Agent, AgentConfiguration, AgentInputMapping, AgentTeam, PromptVersion } from '~/types'

export interface PipelineItem {
  agent: Agent
  team?: AgentTeam
  config: AgentConfiguration
  /** 1-based position in the run order */
  position: number
}

// "Row Text" and "row-text" should both land on a "row_text" variable
function normalizeName(name: string) {
  return name.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

function defaultConfig(agent: Agent): AgentConfiguration {
  return {
    prompt_version_id: agent.default_prompt_version_id || undefined,
    model_id: agent.default_model_id || undefined,
    temperature: undefined,
    max_tokens: undefined,
    is_active: true,
  }
}

/**
 * The agents of an experiment as one ordered pipeline.
 *
 * The backend runs agents one after another by `execution_order`, and the last
 * agent's output is the result, so a list is the whole model. This composable
 * works directly on the form's configuration record (the order lives in each
 * config's `execution_order`) and keeps mappings consistent with that order.
 */
export function useAgentPipeline(options: {
  agentTeams: Ref<readonly AgentTeam[] | null | undefined>
  configurations: Ref<Record<number, AgentConfiguration>>
  promptVersions: Ref<readonly PromptVersion[] | null | undefined>
  datasetHeaders: Ref<readonly string[]>
}) {
  const { agentTeams, configurations, promptVersions, datasetHeaders } = options

  const catalog = computed(() => {
    const byId = new Map<number, { agent: Agent, team: AgentTeam }>()
    agentTeams.value?.forEach(team => team.agents?.forEach(agent => byId.set(agent.id, { agent, team })))
    return byId
  })

  const items = computed<PipelineItem[]>(() => {
    const found: Omit<PipelineItem, 'position'>[] = []
    for (const [key, config] of Object.entries(configurations.value)) {
      const entry = catalog.value.get(Number(key))
      if (entry && config)
        found.push({ agent: entry.agent, team: entry.team, config })
    }
    found.sort((a, b) =>
      (a.config.execution_order ?? Number.POSITIVE_INFINITY) - (b.config.execution_order ?? Number.POSITIVE_INFINITY)
      || a.agent.id - b.agent.id)
    return found.map((item, index) => ({ ...item, position: index + 1 }))
  })

  const addedIds = computed(() => new Set(items.value.map(item => item.agent.id)))

  function variablesOf(agentId: number): string[] {
    const versionId = configurations.value[agentId]?.prompt_version_id
    if (!versionId)
      return []
    return parsePromptVariables(promptVersions.value?.find(v => v.id === versionId)?.variables)
  }

  // Agents that run before this one and are enabled: the only valid "previous agent output" sources
  function upstreamOf(agentId: number): Agent[] {
    const list = items.value
    const index = list.findIndex(item => item.agent.id === agentId)
    return list.slice(0, Math.max(index, 0))
      .filter(item => item.config.is_active !== false)
      .map(item => item.agent)
  }

  function renumber(orderedIds: number[]) {
    orderedIds.forEach((id, index) => {
      const config = configurations.value[id]
      if (config)
        config.execution_order = index + 1
    })
  }

  // Drops mappings that can no longer work: variable gone from the prompt,
  // an agent source that no longer runs earlier, or a column the dataset lacks.
  function pruneMappings() {
    // Prompt versions still loading would make every variable look gone
    if (!promptVersions.value?.length)
      return
    const headers = datasetHeaders.value
    for (const item of items.value) {
      const mappings = item.config.input_mappings
      if (!mappings?.length)
        continue
      const variables = variablesOf(item.agent.id)
      const upstreamIds = new Set(upstreamOf(item.agent.id).map(a => a.id))
      const kept = mappings.filter((m) => {
        if (!variables.includes(m.variable))
          return false
        if (m.source === 'agent')
          return m.sourceAgentId !== undefined && upstreamIds.has(m.sourceAgentId)
        if (m.source === 'dataset' && headers.length > 0)
          return !!m.sourceColumn && headers.includes(m.sourceColumn)
        return true
      })
      if (kept.length !== mappings.length)
        item.config.input_mappings = kept
    }
  }

  // Pre-fills the variables whose name is a dataset column, so the common case needs no clicks
  function autoMap(agentId: number) {
    const config = configurations.value[agentId]
    const headers = datasetHeaders.value
    if (!config || headers.length === 0)
      return
    const mappings = [...(config.input_mappings ?? [])]
    let changed = false
    for (const variable of variablesOf(agentId)) {
      if (mappings.some(m => m.variable === variable))
        continue
      const column = headers.find(h => normalizeName(h) === normalizeName(variable))
      if (column) {
        mappings.push({ variable, source: 'dataset', sourceColumn: column })
        changed = true
      }
    }
    if (changed)
      config.input_mappings = mappings
  }

  function autoMapAll() {
    items.value.forEach(item => autoMap(item.agent.id))
  }

  // Re-checks everything: run when the dataset's columns change
  function syncAll() {
    pruneMappings()
    autoMapAll()
  }

  function add(agent: Agent) {
    if (configurations.value[agent.id])
      return
    configurations.value[agent.id] = { ...defaultConfig(agent), execution_order: items.value.length + 1 }
    autoMap(agent.id)
  }

  function remove(agentId: number) {
    delete configurations.value[agentId]
    renumber(items.value.map(item => item.agent.id))
    pruneMappings()
  }

  // Puts the agent at a 0-based position of the list
  function moveTo(agentId: number, to: number) {
    const ids = items.value.map(item => item.agent.id)
    const from = ids.indexOf(agentId)
    if (from < 0 || to < 0 || to >= ids.length || from === to)
      return false
    ids.splice(to, 0, ids.splice(from, 1)[0]!)
    renumber(ids)
    pruneMappings()
    return true
  }

  function move(agentId: number, delta: -1 | 1) {
    const from = items.value.findIndex(item => item.agent.id === agentId)
    return moveTo(agentId, from + delta)
  }

  function update(agentId: number, field: keyof AgentConfiguration, value: unknown) {
    const config = configurations.value[agentId]
    if (!config)
      return
    Object.assign(config, { [field]: value })
    if (field === 'prompt_version_id') {
      pruneMappings()
      autoMap(agentId)
    }
    else if (field === 'is_active') {
      pruneMappings()
    }
  }

  function reset(agentId: number) {
    const entry = catalog.value.get(agentId)
    const config = configurations.value[agentId]
    if (!entry || !config)
      return
    configurations.value[agentId] = { ...defaultConfig(entry.agent), execution_order: config.execution_order }
    autoMap(agentId)
  }

  function setMapping(agentId: number, mapping: AgentInputMapping) {
    const config = configurations.value[agentId]
    if (!config)
      return
    const others = (config.input_mappings ?? []).filter(m => m.variable !== mapping.variable)
    config.input_mappings = [...others, mapping]
  }

  function removeMapping(agentId: number, variable: string) {
    const config = configurations.value[agentId]
    if (config)
      config.input_mappings = (config.input_mappings ?? []).filter(m => m.variable !== variable)
  }

  // Order computed elsewhere (the graph view) becomes the list order; ties keep their current order
  function applyOrder(order: Map<number, number>) {
    const ids = items.value
      .map(item => item.agent.id)
      .sort((a, b) => (order.get(a) ?? Number.POSITIVE_INFINITY) - (order.get(b) ?? Number.POSITIVE_INFINITY))
    renumber(ids)
    pruneMappings()
  }

  // What still blocks this agent from running, in words
  function issuesOf(agentId: number): string[] {
    const config = configurations.value[agentId]
    if (!config || config.is_active === false)
      return []
    const issues: string[] = []
    if (!config.prompt_version_id)
      issues.push('Choose a prompt version')
    if (!config.model_id)
      issues.push('Choose a model')
    const mapped = new Set((config.input_mappings ?? []).filter(isMappingComplete).map(m => m.variable))
    const unmapped = variablesOf(agentId).filter(v => !mapped.has(v))
    if (unmapped.length > 0)
      issues.push(unmapped.length === 1 ? `Map variable ${unmapped[0]}` : `Map ${unmapped.length} variables`)
    return issues
  }

  return {
    items,
    addedIds,
    catalog,
    variablesOf,
    upstreamOf,
    add,
    remove,
    move,
    moveTo,
    update,
    reset,
    setMapping,
    removeMapping,
    applyOrder,
    autoMap,
    autoMapAll,
    syncAll,
    issuesOf,
  }
}
