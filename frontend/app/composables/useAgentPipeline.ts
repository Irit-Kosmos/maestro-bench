import type { Agent, AgentConfiguration, AgentInputMapping, PromptVersion } from '~/types'

/** One run of an agent in the experiment: see utils/steps */
export interface PipelineItem {
  /** Key of the step in the configurations: the agent's id, then "12#2"… */
  key: string
  agent: Agent
  /** The agent's name, then "name #2"… */
  label: string
  /** Which run of its agent it is, from 1 */
  instance: number
  config: AgentConfiguration
  /** 1-based position in the run order */
  position: number
}

/** A step another one may read the output of */
export interface StepRef {
  key: string
  label: string
  agent: Agent
}

// "Row Text" and "row-text" should both land on a "row_text" variable
function normalizeName(name: string) {
  return name.trim().toLowerCase().replace(/[\s-]+/g, '_')
}

/** The configuration an agent starts with in an experiment: its own defaults */
export function defaultAgentConfig(agent: Agent): AgentConfiguration {
  if (agent.kind === 'aggregator') {
    return {
      formulas: DEFAULT_FORMULAS.map(f => ({ ...f })),
      is_active: true,
    }
  }
  return {
    prompt_version_id: agent.default_prompt_version_id || undefined,
    model_id: agent.default_model_id || undefined,
    temperature: undefined,
    max_tokens: undefined,
    is_active: true,
  }
}

/**
 * The steps of an experiment as one ordered pipeline.
 *
 * The backend runs steps one after another by `execution_order`, and the last
 * step's output is the result, so a list is the whole model. An agent may be a
 * step several times: the steps are told apart by their key (see utils/steps).
 * This composable works directly on the form's configuration record (the order
 * lives in each config's `execution_order`) and keeps mappings consistent with
 * that order.
 */
export function useAgentPipeline(options: {
  agents: Ref<readonly Agent[] | null | undefined>
  configurations: Ref<Record<string, AgentConfiguration>>
  promptVersions: Ref<readonly PromptVersion[] | null | undefined>
  datasetHeaders: Ref<readonly string[]>
  /** Variables a step has to map besides its prompt's, by step key: the ones a prompt variation adds */
  extraVariables?: Ref<Record<string, readonly string[]>>
}) {
  const { agents, configurations, promptVersions, datasetHeaders } = options
  const extraVariables = options.extraVariables ?? ref<Record<string, readonly string[]>>({})

  const catalog = computed(() => {
    return new Map<number, Agent>((agents.value ?? []).map(agent => [agent.id, agent]))
  })

  const items = computed<PipelineItem[]>(() => {
    const found: Omit<PipelineItem, 'position'>[] = []
    for (const [key, config] of Object.entries(configurations.value)) {
      const { agentId, instance } = splitStep(key)
      const agent = catalog.value.get(agentId)
      if (agent && config)
        found.push({ key, agent, label: stepLabel(agent.name, instance), instance, config })
    }
    found.sort((a, b) =>
      (a.config.execution_order ?? Number.POSITIVE_INFINITY) - (b.config.execution_order ?? Number.POSITIVE_INFINITY)
      || a.agent.id - b.agent.id
      || a.instance - b.instance)
    return found.map((item, index) => ({ ...item, position: index + 1 }))
  })

  // How many times each agent is in the experiment
  const addedCounts = computed(() => {
    const counts = new Map<number, number>()
    for (const item of items.value)
      counts.set(item.agent.id, (counts.get(item.agent.id) ?? 0) + 1)
    return counts
  })

  function isAggregator(key: string) {
    return catalog.value.get(agentIdOfStep(key))?.kind === 'aggregator'
  }

  function variablesOf(key: string): string[] {
    if (isAggregator(key))
      return formulaVariables(configurations.value[key]?.formulas)
    const versionId = configurations.value[key]?.prompt_version_id
    if (!versionId)
      return []
    return parsePromptVariables(promptVersions.value?.find(v => v.id === versionId)?.variables)
  }

  // What the step's mappings are for: its prompt's variables and those of its prompt variations
  function mappableOf(key: string): string[] {
    return [...new Set([...variablesOf(key), ...(extraVariables.value[key] ?? [])])]
  }

  // Steps that run before this one and are enabled: the only valid "previous agent output" sources
  function upstreamOf(key: string): StepRef[] {
    const list = items.value
    const index = list.findIndex(item => item.key === key)
    return list.slice(0, Math.max(index, 0))
      .filter(item => item.config.is_active !== false)
      .map(({ key, label, agent }) => ({ key, label, agent }))
  }

  function renumber(orderedKeys: string[]) {
    orderedKeys.forEach((key, index) => {
      const config = configurations.value[key]
      if (config)
        config.execution_order = index + 1
    })
  }

  // Drops mappings that can no longer work: variable gone from the prompt,
  // a step source that no longer runs earlier, or a column the dataset lacks.
  function pruneMappings() {
    // Prompt versions still loading would make every variable look gone
    if (!promptVersions.value?.length)
      return
    const headers = datasetHeaders.value
    for (const item of items.value) {
      const mappings = item.config.input_mappings
      if (!mappings?.length)
        continue
      const variables = mappableOf(item.key)
      const upstreamKeys = new Set(upstreamOf(item.key).map(step => step.key))
      // Formulas change on every keystroke: an aggregator keeps the mappings of variables it
      // no longer reads, so retyping a name finds its value back (the backend ignores the extra ones)
      const aggregator = isAggregator(item.key)
      const kept = mappings.filter((m) => {
        if (!aggregator && !variables.includes(m.variable))
          return false
        if (m.source === 'agent') {
          const source = mappingSource(m)
          return source !== undefined && upstreamKeys.has(source)
        }
        if (m.source === 'dataset' && headers.length > 0)
          return !!m.sourceColumn && headers.includes(m.sourceColumn)
        return true
      })
      if (kept.length !== mappings.length)
        item.config.input_mappings = kept
    }
  }

  // Pre-fills the variables whose name is a dataset column, so the common case needs no clicks.
  // Not for aggregators: their variables appear while a name is being typed.
  function autoMap(key: string) {
    const config = configurations.value[key]
    const headers = datasetHeaders.value
    if (!config || headers.length === 0 || isAggregator(key))
      return
    const mappings = [...(config.input_mappings ?? [])]
    let changed = false
    for (const variable of mappableOf(key)) {
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
    items.value.forEach(item => autoMap(item.key))
  }

  // Re-checks everything: run when the dataset's columns change
  function syncAll() {
    pruneMappings()
    autoMapAll()
  }

  /**
   * Adds a run of the agent, after the others. An agent already there is added again, as a copy of its
   * first step (the same settings, the same mappings), so only what differs has to be changed.
   * Returns the key of the new step.
   */
  function add(agent: Agent): string {
    const instance = nextInstance(agent.id, Object.keys(configurations.value))
    const key = stepKey(agent.id, instance)
    const first = items.value.find(item => item.agent.id === agent.id)
    const config = first ? JSON.parse(JSON.stringify(first.config)) as AgentConfiguration : defaultAgentConfig(agent)
    configurations.value[key] = { ...config, is_active: true, execution_order: items.value.length + 1 }
    autoMap(key)
    return key
  }

  function remove(key: string) {
    delete configurations.value[key]
    renumber(items.value.map(item => item.key))
    pruneMappings()
  }

  // Puts the step at a 0-based position of the list
  function moveTo(key: string, to: number) {
    const keys = items.value.map(item => item.key)
    const from = keys.indexOf(key)
    if (from < 0 || to < 0 || to >= keys.length || from === to)
      return false
    keys.splice(to, 0, keys.splice(from, 1)[0]!)
    renumber(keys)
    pruneMappings()
    return true
  }

  function move(key: string, delta: -1 | 1) {
    const from = items.value.findIndex(item => item.key === key)
    return moveTo(key, from + delta)
  }

  function update(key: string, field: keyof AgentConfiguration, value: unknown) {
    const config = configurations.value[key]
    if (!config)
      return
    Object.assign(config, { [field]: value })
    if (field === 'prompt_version_id') {
      pruneMappings()
      autoMap(key)
    }
    else if (field === 'is_active') {
      pruneMappings()
    }
  }

  function reset(key: string) {
    const agent = catalog.value.get(agentIdOfStep(key))
    const config = configurations.value[key]
    if (!agent || !config)
      return
    configurations.value[key] = { ...defaultAgentConfig(agent), execution_order: config.execution_order }
    autoMap(key)
  }

  function setMapping(key: string, mapping: AgentInputMapping) {
    const config = configurations.value[key]
    if (!config)
      return
    const others = (config.input_mappings ?? []).filter(m => m.variable !== mapping.variable)
    config.input_mappings = [...others, mapping]
  }

  function removeMapping(key: string, variable: string) {
    const config = configurations.value[key]
    if (config)
      config.input_mappings = (config.input_mappings ?? []).filter(m => m.variable !== variable)
  }

  // Order computed elsewhere (the graph view) becomes the list order; ties keep their current order
  function applyOrder(order: Map<string, number>) {
    const keys = items.value
      .map(item => item.key)
      .sort((a, b) => (order.get(a) ?? Number.POSITIVE_INFINITY) - (order.get(b) ?? Number.POSITIVE_INFINITY))
    renumber(keys)
    pruneMappings()
  }

  // What still blocks this step from running, in words
  function issuesOf(key: string): string[] {
    const config = configurations.value[key]
    if (!config || config.is_active === false)
      return []
    if (isAggregator(key)) {
      const errors = formulaErrorsOf(config.formulas)?.errors.filter(Boolean).length ?? 0
      return [
        ...aggregatorIssues(config),
        ...(errors > 0 ? [errors === 1 ? 'Fix a formula' : `Fix ${errors} formulas`] : []),
      ]
    }
    const issues: string[] = []
    if (!config.prompt_version_id)
      issues.push('Choose a prompt version')
    if (!config.model_id)
      issues.push('Choose a model')
    const mapped = new Set((config.input_mappings ?? []).filter(isMappingComplete).map(m => m.variable))
    const unmapped = variablesOf(key).filter(v => !mapped.has(v))
    if (unmapped.length > 0)
      issues.push(unmapped.length === 1 ? `Map variable ${unmapped[0]}` : `Map ${unmapped.length} variables`)
    return issues
  }

  return {
    items,
    addedCounts,
    catalog,
    isAggregator,
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
