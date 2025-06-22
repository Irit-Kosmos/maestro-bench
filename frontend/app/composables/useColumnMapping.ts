/**
 * Composable for managing dataset column mappings
 */
export function useColumnMapping() {
  // Column mapping helper functions
  const addColumnMapping = (requestConfig: Ref<{ columnMappings: Array<any> }>) => {
    requestConfig.value.columnMappings.push({
      id: crypto.randomUUID(),
      sourceColumn: '',
      targetField: '',
    })
  }

  const removeColumnMapping = (id: string, requestConfig: Ref<{ columnMappings: Array<any> }>) => {
    const index = requestConfig.value.columnMappings.findIndex(mapping => mapping.id === id)
    if (index > -1) {
      requestConfig.value.columnMappings.splice(index, 1)
    }
  }

  const updateColumnMapping = (
    id: string,
    field: 'sourceColumn' | 'targetField',
    value: string,
    requestConfig: Ref<{ columnMappings: Array<any> }>,
  ) => {
    const mapping = requestConfig.value.columnMappings.find(m => m.id === id)
    if (mapping) {
      mapping[field] = value
    }
  }

  // Setup default mappings based on dataset headers
  const setupDefaultMappings = (
    datasetHeaders: Ref<string[]>,
    requestConfig: Ref<{ columnMappings: Array<any> }>,
  ) => {
    const defaultMappings = []
    if (datasetHeaders.value.includes('question')) {
      defaultMappings.push({
        id: crypto.randomUUID(),
        sourceColumn: 'question',
        targetField: 'question',
      })
    }
    if (datasetHeaders.value.includes('desired_answer')) {
      defaultMappings.push({
        id: crypto.randomUUID(),
        sourceColumn: 'desired_answer',
        targetField: 'reference_answer',
      })
    }
    // Only set defaults if no mappings exist yet
    if (requestConfig.value.columnMappings.length === 0) {
      requestConfig.value.columnMappings = defaultMappings
    }
  }

  return {
    addColumnMapping,
    removeColumnMapping,
    updateColumnMapping,
    setupDefaultMappings,
  }
}
