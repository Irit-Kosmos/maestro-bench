import type { AgentTeam } from '~/types'

/**
 * Composable for managing agent teams data and operations
 */
export function useAgentTeams() {
  const { $api } = useNuxtApp()

  // Fetch agent teams with auto-refresh capability
  const { data: agentTeams, refresh, pending, error } = useMyLazyFetch<AgentTeam[]>('/agent-teams')

  // Get available agent teams for experiment creation
  const availableTeams = computed(() => {
    if (!agentTeams.value || agentTeams.value.length === 0)
      return []
    return agentTeams.value.map(team => ({
      id: team.id,
      name: team.name,
      description: team.description,
    }))
  })

  // Create a new agent team
  async function createTeam(teamData: { name: string, description: string, agent_ids?: number[] }) {
    try {
      const response = await $api('/agent-teams', {
        method: 'POST',
        body: teamData,
      })

      // Refresh the teams list
      await refresh()

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating team:', error)
      return { success: false, error: 'Failed to create team' }
    }
  }

  // Update an agent team
  async function updateTeam(teamId: string, teamData: { name?: string, description?: string, agent_ids?: number[] }) {
    try {
      const response = await $api(`/agent-teams/${teamId}`, {
        method: 'PUT',
        body: teamData,
      })

      // Refresh the teams list
      await refresh()

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating team:', error)
      return { success: false, error: 'Failed to update team' }
    }
  }

  // Delete an agent team
  async function deleteTeam(teamId: string) {
    try {
      await $api(`/agent-teams/${teamId}`, {
        method: 'DELETE',
      })

      // Refresh the teams list
      await refresh()

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting team:', error)
      return { success: false, error: 'Failed to delete team' }
    }
  }

  return {
    agentTeams: readonly(computed(() => agentTeams.value ?? null)),
    availableTeams: readonly(availableTeams),
    pending: readonly(pending),
    error: readonly(error),
    refresh,
    createTeam,
    updateTeam,
    deleteTeam,
  }
}
