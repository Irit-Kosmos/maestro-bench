/**
 * Enhanced toast composable with standardized messages
 */
export function useStandardToast() {
  const toast = useToast()

  // Success messages
  function showCreateSuccess(entityName: string) {
    toast.add({
      title: 'Success',
      description: `${entityName} created successfully!`,
      color: 'success',
      icon: 'i-lucide:check-circle',
    })
  }

  function showUpdateSuccess(entityName: string) {
    toast.add({
      title: 'Success',
      description: `${entityName} updated successfully!`,
      color: 'success',
      icon: 'i-lucide:check-circle',
    })
  }

  function showDeleteSuccess(entityName: string) {
    toast.add({
      title: 'Success',
      description: `${entityName} deleted successfully!`,
      color: 'success',
      icon: 'i-lucide:check-circle',
    })
  }

  // Error messages
  function showCreateError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to create ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }

  function showUpdateError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to update ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }

  function showDeleteError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to delete ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }

  function showLoadError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to load ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-lucide:alert-circle',
    })
  }

  // Generic messages
  function showComingSoon(feature: string) {
    toast.add({
      title: 'Coming Soon',
      description: `${feature} feature coming soon!`,
      color: 'info',
      icon: 'i-lucide:info',
    })
  }

  function showNotFound(entityName: string) {
    toast.add({
      title: 'Not Found',
      description: `${entityName} not found.`,
      color: 'error',
      icon: 'i-lucide:search-x',
    })
  }

  return {
    showCreateSuccess,
    showUpdateSuccess,
    showDeleteSuccess,
    showCreateError,
    showUpdateError,
    showDeleteError,
    showLoadError,
    showComingSoon,
    showNotFound,
  }
}
