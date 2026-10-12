import type { CreateAgentForm } from '~/types'

/**
 * Composable for managing individual agents
 */
export function useAgents() {
  const { $api } = useNuxtApp()

  // Create a new agent
  async function createAgent(agentData: CreateAgentForm) {
    try {
      const response = await $api('/agents', {
        method: 'POST',
        body: agentData,
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
