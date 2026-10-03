import { apiErrorMessage } from '~/composables/useAnalyses'

/**
 * Composable for handling experiment submission
 */
export function useExperimentSubmission() {
  const { createExperiment } = useExperiments()
  const { createBatch } = useBatches()
  const toast = useToast()

  async function handleSubmit(experimentData: any) {
    try {
      const result = await createExperiment(experimentData)

      if (result.success) {
        toast.add({
          title: 'Success',
          description: 'Experiment created successfully!',
          color: 'success',
          icon: 'i-ph:check-circle-bold',
        })
        await navigateTo('/')
        return { success: true }
      }
      else {
        toast.add({
          title: 'Error',
          description: 'Failed to create experiment. Please try again.',
          color: 'error',
          icon: 'i-ph:warning-circle-bold',
        })
        return { success: false, error: 'Creation failed' }
      }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      toast.add({
        title: 'Error',
        description: 'An unexpected error occurred. Please try again.',
        color: 'error',
        icon: 'i-ph:warning-circle-bold',
      })
      return { success: false, error }
    }
  }

  // One experiment per combination of the variations, started together
  async function handleBatchSubmit(batch: Parameters<typeof createBatch>[0], experimentCount: number) {
    const result = await createBatch(batch)
    if (result.success) {
      toast.add({
        title: 'Batch started',
        description: `${experimentCount} experiments are running.`,
        color: 'success',
        icon: 'i-ph:check-circle-bold',
      })
      await navigateTo(`/batches/${result.data.id}`)
      return { success: true }
    }
    toast.add({
      title: 'Error',
      description: apiErrorMessage(result.error) ?? 'Failed to create the batch. Please try again.',
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
    })
    return { success: false, error: result.error }
  }

  async function handleCancel() {
    await navigateTo('/')
  }

  return {
    handleSubmit,
    handleBatchSubmit,
    handleCancel,
  }
}
