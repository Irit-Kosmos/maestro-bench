import type { Experiment, ExperimentStats } from '~/types'

const { $api } = useNuxtApp()

/**
 * Composable for managing experiments data and operations
 */
export function useExperiments() {
  // Fetch experiments with auto-refresh capability
  const { data: experiments, refresh, pending, error } = useMyLazyFetch<Experiment[]>('/experiments')

  // Computed statistics for dashboard
  const stats = computed((): ExperimentStats => {
    if (!experiments.value) {
      return { total: 0, completed: 0, running: 0 }
    }

    const total = experiments.value.length
    const completed = experiments.value.filter(exp => exp.status === 'completed').length
    const running = experiments.value.filter(exp => exp.status === 'running').length

    return {
      total,
      completed,
      running,
    }
  })

  // Recent experiments for dashboard (limit to 5 most recent)
  const recentExperiments = computed(() => {
    if (!experiments.value)
      return null
    return experiments.value
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 5)
      .map(exp => ({
        ...exp,
        agent_configs: exp.agent_configs ? [...exp.agent_configs] : undefined,
      }))
  })

  // Create a new experiment
  const createExperiment = async (experimentData: { name: string, dataset_id: number }) => {
    try {
      const response = await $api('/experiments', {
        method: 'POST',
        body: experimentData,
      })

      // Refresh the experiments list
      await refresh()

      return { success: true, data: response }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      return { success: false, error }
    }
  }

  // Delete an experiment
  const deleteExperiment = async (id: number) => {
    try {
      await $api(`/experiments/${id}`, {
        method: 'DELETE',
      })

      // Refresh the experiments list
      await refresh()

      return { success: true }
    }
    catch (error) {
      console.error('Error deleting experiment:', error)
      return { success: false, error }
    }
  }

  return {
    experiments: readonly(experiments),
    stats: readonly(stats),
    recentExperiments,
    pending: readonly(pending),
    error: readonly(error),
    refresh,
    createExperiment,
    deleteExperiment,
  }
}
