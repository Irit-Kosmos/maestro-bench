import type { ExperimentStatus } from '~/types'

/**
 * Utility composable for common UI helpers and formatters
 */
export function useUIHelpers() {
  // Status color mapping for UI badges
  function getStatusColor(status: ExperimentStatus): 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral' {
    const colors = {
      pending: 'warning' as const,
      running: 'info' as const,
      completed: 'success' as const,
      failed: 'error' as const,
    }
    return colors[status] || 'neutral'
  }

  // Format date for display
  function formatDate(dateString: string): string {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Format duration in seconds to human readable
  function formatDuration(seconds: number): string {
    if (seconds < 0)
      return 'N/A'
    const minutes = Math.floor(seconds / 60)
    const secs = (seconds % 60).toFixed(2)
    return `${minutes > 0 ? `${minutes}m ` : ''}${secs}s`
  }

  // Truncate text with ellipsis
  function truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength)
      return text
    return `${text.substring(0, maxLength - 3)}...`
  }

  return {
    getStatusColor,
    formatDate,
    formatDuration,
    truncateText,
  }
}
