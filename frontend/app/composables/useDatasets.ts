import type { CreateDatasetForm, Dataset } from '~/types'

const { $api } = useNuxtApp()

/**
 * Composable for managing datasets data and operations
 */
export function useDatasets() {
  // Fetch datasets with auto-refresh capability
  const { data: datasets, refresh, pending, error } = useMyLazyFetch<Dataset[]>('/datasets')

  // Create a new dataset
  async function createDataset(datasetData: CreateDatasetForm) {
    try {
      const response = await $api('/datasets', {
        method: 'POST',
        body: datasetData,
      })

      // Refresh the datasets list
      await refresh()

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating dataset:', error)
      return { success: false, error }
    }
  }

  // Delete a dataset
  async function deleteDataset(id: number) {
    try {
      await $api(`/datasets/${id}`, {
        method: 'DELETE',
      })

      // Refresh the datasets list
      await refresh()

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting dataset:', error)
      return { success: false, error }
    }
  }

  return {
    datasets: readonly(datasets),
    pending: readonly(pending),
    error: readonly(error),
    refresh,
    createDataset,
    deleteDataset,
  }
}
