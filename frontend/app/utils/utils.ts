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

// Below this many rows, metrics are too noisy to compare: flag the run instead of hiding it
export const SMALL_SAMPLE_ROWS = 30

export function isSmallSample(rows: number | null | undefined): boolean {
  return typeof rows === 'number' && rows < SMALL_SAMPLE_ROWS
}

// "1 row", "2,273 rows"
export function formatRows(rows: number): string {
  return `${rows.toLocaleString('en-US')} ${rows === 1 ? 'row' : 'rows'}`
}
