import type {
  Analysis,
  AnalysisConfig,
  AnalysisForm,
  AnalysisResult,
  AnalysisRunRef,
  ExecutionFields,
} from '~/types'

export const DEFAULT_ANALYSIS_CONFIG: AnalysisConfig = {
  truth_column: '',
  output_path: '',
  value_type: 'numeric',
  metrics: ['rmse', 'mae', 'pearson', 'spearman', 'bias'],
  ignore_case: false,
  n_boot: 1000,
  confidence: 0.95,
  seed: 0,
}

export const EXCLUSION_LABELS: Record<string, string> = {
  agent_error: 'Agent error',
  unparsed_output: 'Output is not JSON',
  path_missing: 'Path not found',
  invalid_value: 'Invalid value',
  truth_missing: 'Missing ground truth',
}

/**
 * Composable for analyses: saved comparisons of executions against a
 * ground-truth column, recomputed by the backend on each request.
 */
export function useAnalyses() {
  const { $api } = useNuxtApp()

  const createAnalysis = (form: AnalysisForm) =>
    $api<Analysis>('/analyses', { method: 'POST', body: form })

  const updateAnalysis = (id: number, form: Partial<AnalysisForm>) =>
    $api<Analysis>(`/analyses/${id}`, { method: 'PUT', body: form })

  const deleteAnalysis = (id: number) =>
    $api(`/analyses/${id}`, { method: 'DELETE' })

  const fetchResults = (id: number) =>
    $api<AnalysisResult>(`/analyses/${id}/results`)

  const computeAnalysis = (config: AnalysisConfig, runs: AnalysisRunRef[]) =>
    $api<AnalysisResult>('/analyses/compute', { method: 'POST', body: { config, runs } })

  const fetchExecutionFields = (executionId: number) =>
    $api<ExecutionFields>(`/executions/${executionId}/analysis-fields`)

  return {
    createAnalysis,
    updateAnalysis,
    deleteAnalysis,
    fetchResults,
    computeAnalysis,
    fetchExecutionFields,
  }
}

/** Error message from a FastAPI error response, if any. */
export function apiErrorMessage(error: unknown): string | undefined {
  const detail = (error as { data?: { detail?: unknown } })?.data?.detail
  return typeof detail === 'string' ? detail : undefined
}
