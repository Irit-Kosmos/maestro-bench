/**
 * Composable for managing experiments data and operations
 */
export function useExperiments() {
  const { $api } = useNuxtApp()

  // Create a new experiment
  const createExperiment = async (experimentData: { name: string, dataset_id: number }) => {
    try {
      const response = await $api('/experiments', {
        method: 'POST',
        body: experimentData,
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      return { success: false, error }
    }
  }

  // Fetch a single experiment by ID
  const fetchExperiment = async (id: number) => {
    try {
      const response = await $api(`/experiments/${id}`)
      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error fetching experiment:', error)
      return { success: false, error }
    }
  }

  // Delete an experiment
  const deleteExperiment = async (id: number) => {
    try {
      await $api(`/experiments/${id}`, {
        method: 'DELETE',
      })

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting experiment:', error)
      return { success: false, error }
    }
  }

  // Re-run an experiment with the same configuration
  const rerunExperiment = async (id: number) => {
    try {
      const response = await $api(`/experiments/${id}/rerun`, {
        method: 'POST',
      })

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error re-running experiment:', error)
      return { success: false, error }
    }
  }

  return {
    createExperiment,
    fetchExperiment,
    deleteExperiment,
    rerunExperiment,
  }
}
