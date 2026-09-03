import type { ExperimentExecution } from '~/types'

/**
 * Composable for managing experiment executions and their detailed configurations
 */
export function useExperimentExecutions() {
  const { $api } = useNuxtApp()

  // Fetch all executions for an experiment
  const fetchExperimentExecutions = async (experimentId: number) => {
    try {
      const response = await $api(`/experiments/${experimentId}/executions`)
      return { success: true, data: response as ExperimentExecution[] }
    }
    catch (error) {
      console.error('Error fetching experiment executions:', error)
      return { success: false, error }
    }
  }

  return {
    fetchExperimentExecutions,
  }
}
