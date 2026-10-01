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

// Helper function to stringify variables array to string
export function stringifyVariables(variablesArray: string[]): string {
  if (!variablesArray || variablesArray.length === 0)
    return ''
  return JSON.stringify(variablesArray)
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
