import type { AgentInputMapping } from '~/types'

/**
 * An agent may run several times in an experiment. Each run is a *step*, told apart by its key: the id of its agent
 * for the first one ("12"), then "12#2", "12#3"… The backend uses the same keys, and names a step the same way.
 */

export function stepKey(agentId: number, instance = 1): string {
  return instance === 1 ? String(agentId) : `${agentId}#${instance}`
}

/** The agent and the run (1 for the first) a step key stands for */
export function splitStep(key: string): { agentId: number, instance: number } {
  const [agent = '', instance] = key.split('#')
  return { agentId: Number.parseInt(agent), instance: instance ? Number.parseInt(instance) : 1 }
}

export function agentIdOfStep(key: string): number {
  return splitStep(key).agentId
}

/** What a step is called: its agent's name, then "name #2", "name #3"… */
export function stepLabel(name: string, instance: number): string {
  return instance === 1 ? name : `${name} #${instance}`
}

/** The number of the next run of an agent, given the keys of the steps already there: the first one free */
export function nextInstance(agentId: number, keys: Iterable<string>): number {
  const taken = new Set([...keys].map(splitStep).filter(step => step.agentId === agentId).map(step => step.instance))
  let instance = 1
  while (taken.has(instance))
    instance++
  return instance
}

/** The step an input mapping reads. Mappings saved before agents could repeat name an agent by id only. */
export function mappingSource(mapping: AgentInputMapping): string | undefined {
  if (mapping.sourceStep !== undefined)
    return mapping.sourceStep
  return mapping.sourceAgentId === undefined ? undefined : String(mapping.sourceAgentId)
}
