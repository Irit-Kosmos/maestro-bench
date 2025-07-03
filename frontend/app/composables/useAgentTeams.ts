/**
 * Composable for managing agent teams operations
 */
export function useAgentTeams() {
  const { $api } = useNuxtApp()

  // Create a new agent team
  async function createTeam(teamData: { name: string, description: string, agent_ids?: number[] }) {
    try {
      const response = await $api('/agent-teams', {
        method: 'POST',
        body: teamData,
      })

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

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting team:', error)
      return { success: false, error: 'Failed to delete team' }
    }
  }

  return {
    createTeam,
    updateTeam,
    deleteTeam,
  }
}
