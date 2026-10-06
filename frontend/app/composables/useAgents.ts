import type { AgentTeam, CreateAgentForm } from '~/types'

/**
 * Composable for managing individual agents
 */
export function useAgents() {
  const { $api } = useNuxtApp()
  const { createTeam } = useAgentTeams()

  // Create a new agent. Without a team (`team_id` 0: the workspace has none yet) it goes in a "Default" team,
  // so a first agent never starts with a detour through teams
  async function createAgent(agentData: CreateAgentForm) {
    try {
      let teamId = agentData.team_id
      if (!(teamId > 0)) {
        const team = await createTeam({ name: 'Default' })
        if (!team.success)
          return { success: false, error: 'Failed to create the default team' }
        teamId = (team.data as AgentTeam).id
      }

      const response = await $api('/agents', {
        method: 'POST',
        body: { ...agentData, team_id: teamId },
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating agent:', error)
      return { success: false, error: 'Failed to create agent' }
    }
  }

  // Update an agent
  async function updateAgent(agentId: number, agentData: Partial<CreateAgentForm>) {
    try {
      const response = await $api(`/agents/${agentId}`, {
        method: 'PUT',
        body: agentData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating agent:', error)
      return { success: false, error: 'Failed to update agent' }
    }
  }

  // Delete an agent
  async function deleteAgent(agentId: number) {
    try {
      await $api(`/agents/${agentId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting agent:', error)
      return { success: false, error: 'Failed to delete agent' }
    }
  }

  return {
    createAgent,
    updateAgent,
    deleteAgent,
  }
}
