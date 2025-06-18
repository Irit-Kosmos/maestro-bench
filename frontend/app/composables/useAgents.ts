import type { Agent, CreateAgentForm } from '~/types'

const { $api } = useNuxtApp()

/**
 * Composable for managing individual agents
 */
export function useAgents() {
  // Fetch agents with auto-refresh capability
  const { data: agents, refresh, pending, error } = useMyLazyFetch<Agent[]>('/agents')

  // Create a new agent
  async function createAgent(agentData: CreateAgentForm) {
    try {
      const response = await $api('/agents', {
        method: 'POST',
        body: agentData,
      })

      // Refresh the agents list
      await refresh()

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

      // Refresh the agents list
      await refresh()

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

      // Refresh the agents list
      await refresh()

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting agent:', error)
      return { success: false, error: 'Failed to delete agent' }
    }
  }

  return {
    agents: readonly(agents),
    pending: readonly(pending),
    error: readonly(error),
    refresh,
    createAgent,
    updateAgent,
    deleteAgent,
  }
}
