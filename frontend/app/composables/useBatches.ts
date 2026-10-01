import type { Variation } from '~/types'

/**
 * Composable for batches: groups of experiments generated from one base
 * configuration by varying a model, a prompt version or a temperature.
 */
export function useBatches() {
  const { $api } = useNuxtApp()

  async function createBatch(batch: {
    name: string
    description?: string
    base_experiment_id?: number
    config: Record<string, unknown>
    variations: Variation[]
    skip_base_point?: boolean
  }) {
    try {
      return { success: true as const, data: await $api<{ id: number }>('/batches', { method: 'POST', body: batch }) }
    }
    catch (error) {
      console.error('Error creating batch:', error)
      return { success: false as const, error }
    }
  }

  async function cancelBatch(id: number) {
    try {
      return { success: true as const, data: await $api<{ cancelled: number }>(`/batches/${id}/cancel`, { method: 'POST' }) }
    }
    catch (error) {
      console.error('Error cancelling batch:', error)
      return { success: false as const, error }
    }
  }

  async function deleteBatch(id: number) {
    try {
      await $api(`/batches/${id}`, { method: 'DELETE' })
      return { success: true as const }
    }
    catch (error) {
      console.error('Error deleting batch:', error)
      return { success: false as const, error }
    }
  }

  return { createBatch, cancelBatch, deleteBatch }
}
