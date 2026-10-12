import type { Agent } from '~/types'

/** Menu entries to pick an agent */
export function agentMenuItems(agents: readonly Agent[], onSelect: (agent: Agent) => void) {
  return agents.map(agent => ({
    label: agent.name,
    icon: agent.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold',
    onSelect: () => onSelect(agent),
  }))
}
