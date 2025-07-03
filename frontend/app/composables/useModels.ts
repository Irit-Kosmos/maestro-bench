/**
 * Composable for managing LLM models
 */
export function useModels() {
  const { $api } = useNuxtApp()

  // Reactive data fetching for models
  const { data: models, pending: modelsPending, refresh: refreshModels } = useMyLazyFetch<any[]>('/models/all')

  // Fetch all models (including inactive)
  async function getAllModels() {
    try {
      const response = await $api('/models/all')
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching all models:', error)
      return { success: false, error: 'Failed to fetch models' }
    }
  }

  // Create a new model
  async function createModel(modelData: {
    name: string
    provider: string
    description?: string
    max_tokens?: number
    is_active?: boolean
  }) {
    try {
      const response = await $api('/models', {
        method: 'POST',
        body: modelData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating model:', error)
      return { success: false, error: 'Failed to create model' }
    }
  }

  // Update a model
  async function updateModel(modelId: number, modelData: {
    name?: string
    provider?: string
    description?: string
    max_tokens?: number
    is_active?: boolean
  }) {
    try {
      const response = await $api(`/models/${modelId}`, {
        method: 'PUT',
        body: modelData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error updating model:', error)
      return { success: false, error: 'Failed to update model' }
    }
  }

  // Delete a model
  async function deleteModel(modelId: number) {
    try {
      await $api(`/models/${modelId}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting model:', error)
      return { success: false, error: 'Failed to delete model' }
    }
  }

  // Toggle model active status
  async function toggleModelStatus(modelId: number) {
    try {
      const response = await $api(`/models/${modelId}/toggle-status`, {
        method: 'PATCH',
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error toggling model status:', error)
      return { success: false, error: 'Failed to toggle model status' }
    }
  }

  return {
    models,
    modelsPending,
    refreshModels,
    getAllModels,
    createModel,
    updateModel,
    deleteModel,
    toggleModelStatus,
  }
}
