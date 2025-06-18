/**
 * Composable for handling user notifications and messages
 */
export function useNotifications() {
  const message = ref('')
  const messageType = ref<'success' | 'error' | 'info' | 'warning'>('info')
  const showMessage = ref(false)

  function showNotification(text: string, type: 'success' | 'error' | 'info' | 'warning' = 'info', duration = 3000) {
    message.value = text
    messageType.value = type
    showMessage.value = true

    if (duration > 0) {
      setTimeout(() => {
        hideNotification()
      }, duration)
    }
  }

  function hideNotification() {
    showMessage.value = false
    setTimeout(() => {
      message.value = ''
    }, 300) // Wait for animation
  }

  function showSuccess(text: string, duration = 3000) {
    showNotification(text, 'success', duration)
  }

  function showError(text: string, duration = 5000) {
    showNotification(text, 'error', duration)
  }

  function showInfo(text: string, duration = 3000) {
    showNotification(text, 'info', duration)
  }

  function showWarning(text: string, duration = 3000) {
    showNotification(text, 'warning', duration)
  }

  return {
    message: readonly(message),
    messageType: readonly(messageType),
    showMessage: readonly(showMessage),
    showNotification,
    hideNotification,
    showSuccess,
    showError,
    showInfo,
    showWarning,
  }
}
