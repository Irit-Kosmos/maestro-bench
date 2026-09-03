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

  return {
    showCreateSuccess,
    showUpdateSuccess,
    showDeleteSuccess,
    showCreateError,
    showUpdateError,
    showDeleteError,
  }
}
