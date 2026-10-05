import { apiErrorMessage } from '~/composables/useAnalyses'

/**
 * Composable for handling experiment submission
 */
export function useExperimentSubmission() {
  const { createExperiment } = useExperiments()
  const { createBatch } = useBatches()
  const { ok, fail } = useStandardToast()
  const router = useRouter()

  async function handleSubmit(experimentData: any) {
    try {
      const result = await createExperiment(experimentData)

      if (result.success) {
        const created = result.data as { id: number, status?: string }
        // A workspace already running as many experiments as it may queues the new one
        ok(created.status === 'queued' ? 'Experiment queued' : 'Experiment started')
        // Land on the run itself: its progress is live there
        await navigateTo(`/experiments/${created.id}`)
        return { success: true }
      }
      else {
        // An aggregator the backend cannot run says why
        fail('Couldn’t create the experiment', apiErrorMessage(result.error) ?? 'Please try again.')
        return { success: false, error: 'Creation failed' }
      }
    }
    catch (error) {
      console.error('Error creating experiment:', error)
      fail('Couldn’t create the experiment', 'An unexpected error occurred. Please try again.')
      return { success: false, error }
    }
  }

  // One experiment per combination of the variations, started together
  async function handleBatchSubmit(batch: Parameters<typeof createBatch>[0], experimentCount: number) {
    const result = await createBatch(batch)
    if (result.success) {
      ok('Batch started', { description: `${experimentCount} experiments are running.` })
      await navigateTo(`/batches/${result.data.id}`)
      return { success: true }
    }
    fail('Couldn’t create the batch', apiErrorMessage(result.error) ?? 'Please try again.')
    return { success: false, error: result.error }
  }

  // Back to where the person came from; a page opened directly has nowhere to go back to
  async function handleCancel() {
    if (router.options.history.state.back)
      router.back()
    else
      await navigateTo('/experiments')
  }

  return {
    handleSubmit,
    handleBatchSubmit,
    handleCancel,
  }
}
