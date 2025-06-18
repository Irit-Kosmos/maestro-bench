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
    if (seconds < 60)
      return `${seconds}s`
    if (seconds < 3600)
      return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
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
