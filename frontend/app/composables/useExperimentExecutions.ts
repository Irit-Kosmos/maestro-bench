import type { ExperimentExecution, ExperimentTrace } from '~/types'

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

  // Fetch detailed execution with configuration
  const fetchExecutionDetails = async (executionId: number) => {
    try {
      const response = await $api(`/executions/${executionId}`)
      return { success: true, data: response as ExperimentExecution }
    }
    catch (error) {
      console.error('Error fetching execution details:', error)
      return { success: false, error }
    }
  }

  // Fetch complete scientific trace of an execution
  const fetchExecutionTrace = async (executionId: number) => {
    try {
      const response = await $api(`/executions/${executionId}/trace`)
      return { success: true, data: response as ExperimentTrace }
    }
    catch (error) {
      console.error('Error fetching execution trace:', error)
      return { success: false, error }
    }
  }

  return {
    fetchExperimentExecutions,
    fetchExecutionDetails,
    fetchExecutionTrace,
  }
}
