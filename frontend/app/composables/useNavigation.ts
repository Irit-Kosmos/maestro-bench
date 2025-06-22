/**
 * Enhanced navigation composable with consistent patterns
 */
export function useNavigation() {
  const toast = useToast()

  // Standard navigation patterns
  async function navigateToExperiment(id: number) {
    await navigateTo(`/experiments/${id}`)
  }

  async function navigateToDataset(id: number) {
    await navigateTo(`/datasets/${id}`)
  }

  async function navigateToAgent(id: number) {
    await navigateTo(`/agents/${id}`)
  }

  async function navigateToModel(id: number) {
    await navigateTo(`/models/${id}`)
  }

  async function navigateToPrompt(id: number) {
    await navigateTo(`/prompts/${id}`)
  }

  // Navigation with error handling
  async function safeNavigateTo(path: string, options?: { replace?: boolean }) {
    try {
      await navigateTo(path, options)
    }
    catch (error) {
      console.error('Navigation error:', error)
      toast.add({
        title: 'Navigation Error',
        description: 'Failed to navigate to the requested page',
        color: 'error',
        icon: 'i-lucide:alert-circle',
      })
    }
  }

  // Go back with fallback
  function goBack(fallbackPath = '/') {
    try {
      if (window.history.length > 1) {
        window.history.back()
      }
      else {
        navigateTo(fallbackPath)
      }
    }
    catch {
      navigateTo(fallbackPath)
    }
  }

  return {
    navigateToExperiment,
    navigateToDataset,
    navigateToAgent,
    navigateToModel,
    navigateToPrompt,
    safeNavigateTo,
    goBack,
  }
}
