import type { Dataset } from '~/types'

interface DatasetPreview {
  file_type: 'csv' | 'json'
  headers: string[]
  sample_data: Record<string, any>[]
  total_rows: number
  total_columns: number
}

interface DatasetPreviewState {
  preview: DatasetPreview | null
  loading: boolean
  error: string | null
}

/**
 * Composable for reading and previewing dataset files
 */
export function useDatasetPreview() {
  const { $api } = useNuxtApp()

  // State for preview data
  const state = reactive<DatasetPreviewState>({
    preview: null,
    loading: false,
    error: null,
  })

  /**
   * Load dataset preview by dataset ID
   */
  async function loadPreview(datasetId: number) {
    state.loading = true
    state.error = null
    state.preview = null

    try {
      const response = await $api(`/datasets/${datasetId}/preview`)
      state.preview = response as DatasetPreview
    }
    catch (error: any) {
      console.error('Error loading dataset preview:', error)
      state.error = error?.data?.detail || 'Failed to load dataset preview'
    }
    finally {
      state.loading = false
    }
  }

  /**
   * Clear preview state
   */
  function clearPreview() {
    state.preview = null
    state.error = null
    state.loading = false
  }

  /**
   * Get formatted file size info
   */
  const fileInfo = computed(() => {
    if (!state.preview)
      return null

    return {
      type: state.preview.file_type.toUpperCase(),
      rows: state.preview.total_rows.toLocaleString('en-US'),
      columns: state.preview.total_columns.toLocaleString('en-US'),
    }
  })

  /**
   * Get headers as display-friendly format
   */
  const displayHeaders = computed(() => {
    if (!state.preview?.headers)
      return []

    return state.preview.headers.map((header, index) => ({
      key: header,
      label: header,
      index,
    }))
  })

  /**
   * Get sample data for table display
   */
  const sampleRows = computed(() => {
    if (!state.preview?.sample_data)
      return []

    return state.preview.sample_data
  })

  /**
   * Check if dataset has preview capability
   */
  function canPreview(dataset: Dataset): boolean {
    if (!dataset.file_path)
      return false

    const extension = dataset.file_path.toLowerCase().split('.').pop()
    return extension === 'csv' || extension === 'json'
  }

  /**
   * Get file extension from dataset
   */
  function getFileExtension(dataset: Dataset): string | null {
    if (!dataset.file_path)
      return null

    return dataset.file_path.toLowerCase().split('.').pop() || null
  }

  return {
    // State
    preview: readonly(toRef(state, 'preview')),
    loading: readonly(toRef(state, 'loading')),
    error: readonly(toRef(state, 'error')),

    // Computed
    fileInfo,
    displayHeaders,
    sampleRows,

    // Actions
    loadPreview,
    clearPreview,
    canPreview,
    getFileExtension,
  }
}
