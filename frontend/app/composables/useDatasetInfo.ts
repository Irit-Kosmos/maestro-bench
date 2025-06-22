/**
 * Composable for getting dataset information including row count for sampling
 */
export function useDatasetInfo() {
  const { $api } = useNuxtApp()

  // Fetch dataset info including row count
  const fetchDatasetInfo = async (datasetId: number) => {
    try {
      const response = await $api(`/datasets/${datasetId}/info`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching dataset info:', error)
      return { success: false, error }
    }
  }

  return {
    fetchDatasetInfo,
  }
}

export interface DatasetInfo {
  id: number
  name: string
  description?: string
  file_type: 'csv' | 'json'
  total_rows: number
  total_columns: number
  headers: string[]
}
