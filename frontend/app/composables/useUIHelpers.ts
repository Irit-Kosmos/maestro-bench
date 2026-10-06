import type { ExperimentStatus } from '~/types'

/**
 * Utility composable for common UI helpers and formatters
 */
export function useUIHelpers() {
  // Status color mapping for UI badges
  function getStatusColor(status: ExperimentStatus): 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral' {
    const colors = {
      pending: 'warning' as const,
      queued: 'neutral' as const,
      running: 'info' as const,
      completed: 'success' as const,
      failed: 'error' as const,
      cancelled: 'neutral' as const,
      interrupted: 'neutral' as const,
      partial: 'warning' as const,
    }
    return colors[status] || 'neutral'
  }

  // Format date for display
  function formatDate(dateString: string): string {
    return parseApiDate(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // Date without the time ("Mar 4, 2026"), for places where a version has to be recognised at a glance
  function formatShortDate(dateString: string): string {
    return parseApiDate(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  }

  // Short relative date for lists ("5m ago", "3d ago", then "Mar 4"); pair with formatDate in a title
  function formatRelativeDate(dateString: string): string {
    const date = parseApiDate(dateString)
    const seconds = Math.round((Date.now() - date.getTime()) / 1000)
    if (seconds < 60)
      return 'Just now'
    const minutes = Math.round(seconds / 60)
    if (minutes < 60)
      return `${minutes}m ago`
    const hours = Math.round(minutes / 60)
    if (hours < 24)
      return `${hours}h ago`
    const days = Math.round(hours / 24)
    if (days < 7)
      return `${days}d ago`
    const sameYear = date.getFullYear() === new Date().getFullYear()
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: sameYear ? undefined : 'numeric' })
  }

  return {
    getStatusColor,
    formatDate,
    formatShortDate,
    formatRelativeDate,
  }
}
