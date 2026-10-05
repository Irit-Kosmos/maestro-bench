/**
 * Composable for managing agent teams operations
 */
export function useAgentTeams() {
  const { $api } = useNuxtApp()

  // Create a new agent team
  async function createTeam(teamData: { name: string, description?: string, agent_ids?: number[] }) {
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

  return {
    createTeam,
  }
}
