import type { Agent, AgentTeam } from '~/types'

/** Menu entries to pick an agent, a label per team above its agents */
export function agentMenuItems(groups: readonly { team: AgentTeam, agents: readonly Agent[] }[], onSelect: (agent: Agent) => void) {
  return groups.flatMap(({ team, agents }) => [
    { type: 'label' as const, label: team.name },
    ...agents.map(agent => ({
      label: agent.name,
      icon: agent.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold',
      onSelect: () => onSelect(agent),
    })),
  ])
}
