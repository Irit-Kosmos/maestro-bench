/**
 * Composable for managing prompts and their versions
 */
export function usePrompts() {
  const { $api } = useNuxtApp()

  // Create a new prompt
  async function createPrompt(promptData: { name: string, description?: string, category?: string, tag_ids?: number[] }) {
    try {
      const response = await $api('/prompts', {
        method: 'POST',
        body: promptData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating prompt:', error)
      return { success: false, error: 'Failed to create prompt' }
    }
  }

  // Update a prompt
  async function updatePrompt(promptId: number, promptData: { name?: string, description?: string, category?: string, tag_ids?: number[] }) {
    try {
      const response = await $api(`/prompts/${promptId}`, {
        method: 'PUT',
        body: promptData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating prompt:', error)
      return { success: false, error: 'Failed to update prompt' }
    }
  }

  // Delete a prompt
  async function deletePrompt(promptId: number) {
    try {
      await $api(`/prompts/${promptId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting prompt:', error)
      return { success: false, error: 'Failed to delete prompt' }
    }
  }

  // Get prompt versions for a specific prompt
  async function getPromptVersions(promptId: number) {
    try {
      const response = await $api(`/prompts/${promptId}/versions`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching prompt versions:', error)
      return { success: false, error: 'Failed to fetch prompt versions' }
    }
  }

  // Create a new prompt version
  async function createPromptVersion(promptId: number, versionData: {
    version: string
    system_prompt?: string | null
    user_prompt?: string | null
    variables?: string | null
    is_active?: boolean
    is_default?: boolean
    notes?: string | null
  }) {
    try {
      const response = await $api(`/prompts/${promptId}/versions`, {
        method: 'POST',
        body: versionData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating prompt version:', error)
      return { success: false, error: 'Failed to create prompt version' }
    }
  }

  // Update a prompt version
  async function updatePromptVersion(versionId: number, versionData: {
    version?: string
    system_prompt?: string | null
    user_prompt?: string | null
    variables?: string | null
    is_active?: boolean
    is_default?: boolean
    notes?: string | null
  }) {
    try {
      const response = await $api(`/prompt-versions/${versionId}`, {
        method: 'PUT',
        body: versionData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating prompt version:', error)
      return { success: false, error: 'Failed to update prompt version' }
    }
  }

  // Delete a prompt version
  async function deletePromptVersion(versionId: number) {
    try {
      await $api(`/prompt-versions/${versionId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting prompt version:', error)
      return { success: false, error: 'Failed to delete prompt version' }
    }
  }

  return {
    createPrompt,
    updatePrompt,
    deletePrompt,
    getPromptVersions,
    createPromptVersion,
    updatePromptVersion,
    deletePromptVersion,
  }
}
