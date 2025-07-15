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
