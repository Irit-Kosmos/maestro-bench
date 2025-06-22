/**
 * Composable for handling experiment submission
 */
export function useExperimentSubmission() {
  const { createExperiment } = useExperiments()
  const toast = useToast()

  async function handleSubmit(experimentData: any) {
    try {
      const result = await createExperiment(experimentData)

      if (result.success) {
        toast.add({
          title: 'Success',
          description: 'Experiment created successfully with modern configuration!',
          color: 'success',
          icon: 'i-lucide:check-circle',
        })
        await navigateTo('/')
        return { success: true }
      }
      else {
        toast.add({
          title: 'Error',
          description: 'Failed to create experiment. Please try again.',
          color: 'error',
          icon: 'i-lucide:alert-circle',
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
        icon: 'i-lucide:alert-circle',
      })
      return { success: false, error }
    }
  }

  async function handleCancel() {
    await navigateTo('/')
  }

  return {
    handleSubmit,
    handleCancel,
  }
}
