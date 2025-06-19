import type { CreateDatasetForm, Dataset } from '~/types'

/**
 * Composable for managing datasets data and operations
 */
export function useDatasets() {
  const { $api } = useNuxtApp()

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

  // Check if a dataset can be previewed
  function canPreview(dataset: Dataset): boolean {
    if (!dataset.file_path)
      return false

    const extension = dataset.file_path.toLowerCase().split('.').pop()
    return extension === 'csv' || extension === 'json'
  }

  // Get file extension from dataset
  function getFileExtension(dataset: Dataset): string | null {
    if (!dataset.file_path)
      return null

    return dataset.file_path.toLowerCase().split('.').pop() || null
  }

  return {
    datasets: readonly(computed(() => datasets.value ?? null)),
    pending: readonly(pending),
    error: readonly(error),
    refresh,
    createDataset,
    deleteDataset,
    canPreview,
    getFileExtension,
  }
}
