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
      icon: 'i-ph:check-circle-bold',
    })
  }

  function showUpdateSuccess(entityName: string) {
    toast.add({
      title: 'Success',
      description: `${entityName} updated successfully!`,
      color: 'success',
      icon: 'i-ph:check-circle-bold',
    })
  }

  function showDeleteSuccess(entityName: string) {
    toast.add({
      title: 'Success',
      description: `${entityName} deleted successfully!`,
      color: 'success',
      icon: 'i-ph:check-circle-bold',
    })
  }

  // Error messages
  function showCreateError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to create ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
    })
  }

  function showUpdateError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to update ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
    })
  }

  function showDeleteError(entityName: string, error?: string) {
    toast.add({
      title: 'Error',
      description: error || `Failed to delete ${entityName.toLowerCase()}. Please try again.`,
      color: 'error',
      icon: 'i-ph:warning-circle-bold',
    })
  }

  return {
    showCreateSuccess,
    showUpdateSuccess,
    showDeleteSuccess,
    showCreateError,
    showUpdateError,
    showDeleteError,
  }
}
