import type { AgentInputMapping } from '~/types'

// Helper function to parse variables string to array
export function parseVariables(variablesString: string): string[] {
  if (!variablesString)
    return []
  try {
    const parsed = JSON.parse(variablesString)
    return Array.isArray(parsed) ? parsed : []
  }
  catch (error) {
    console.warn('Failed to parse variables:', error)
    return []
  }
}

// Variable names of a prompt version ("variables" is a JSON array, or an object keyed by name)
export function parsePromptVariables(variablesJson: string | null | undefined): string[] {
  if (!variablesJson)
    return []
  try {
    const parsed = JSON.parse(variablesJson)
    if (Array.isArray(parsed))
      return parsed
    if (typeof parsed === 'object' && parsed !== null)
      return Object.keys(parsed)
    return []
  }
  catch {
    return []
  }
}

// A mapping only counts once its source is fully chosen (a column, an agent or some text)
export function isMappingComplete(mapping: AgentInputMapping | undefined): boolean {
  if (!mapping)
    return false
  if (mapping.source === 'dataset')
    return !!mapping.sourceColumn
  if (mapping.source === 'agent')
    return mapping.sourceAgentId !== undefined
  return mapping.source === 'static'
}

// Helper function to stringify variables array to string
export function stringifyVariables(variablesArray: string[]): string {
  if (!variablesArray || variablesArray.length === 0)
    return ''
  return JSON.stringify(variablesArray)
}

// Format an analysis metric value (3 decimals, "—" when undefined)
export function formatMetric(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

// Metrics where the best value is the one closest to zero, whatever its sign
const CLOSEST_TO_ZERO_METRICS = new Set(['bias'])

// Rank score of a metric value across runs: the lowest score is the best run
export function metricRankScore(metric: { key: string, lower_is_better: boolean }, value: number): number {
  if (CLOSEST_TO_ZERO_METRICS.has(metric.key))
    return Math.abs(value)
  return metric.lower_is_better ? value : -value
}

// Below this many rows, metrics are too noisy to compare: flag the run instead of hiding it
export const SMALL_SAMPLE_ROWS = 30

export function isSmallSample(rows: number | null | undefined): boolean {
  return typeof rows === 'number' && rows < SMALL_SAMPLE_ROWS
}

// "1 row", "2,273 rows"
export function formatRows(rows: number): string {
  return `${rows.toLocaleString('en-US')} ${rows === 1 ? 'row' : 'rows'}`
}

// The API stores UTC but serializes naive datetimes ("2026-10-01T13:58:48.414969", no "Z"),
// which `new Date()` would read as local time. Treat offset-less strings as UTC.
export function parseApiDate(dateString: string): Date {
  const hasTimeZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(dateString)
  return new Date(hasTimeZone ? dateString : `${dateString.replace(' ', 'T')}Z`)
}

// "$0.42", "$12.30", "<$0.01" for a run too cheap to show, "—" while unknown
export function formatCost(usd: number | null | undefined): string {
  if (usd === null || usd === undefined)
    return '—'
  if (usd > 0 && usd < 0.01)
    return '<$0.01'
  return `$${usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// "842", "12.4k", "3.1M"
export function formatTokens(tokens: number | null | undefined): string {
  if (tokens === null || tokens === undefined)
    return '—'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(tokens)
}

// "42s", "2m 14s", "1h 05m": a run's length at a glance, never fractions of a second
export function formatElapsed(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0)
    return '—'
  const total = Math.round(seconds)
  if (total < 60)
    return `${total}s`
  const minutes = Math.floor(total / 60)
  if (minutes < 60)
    return `${minutes}m ${String(total % 60).padStart(2, '0')}s`
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`
}
