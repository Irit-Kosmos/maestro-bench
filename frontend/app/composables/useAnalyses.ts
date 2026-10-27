// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

import type {
  Analysis,
  AnalysisConfig,
  AnalysisForm,
  AnalysisResult,
  AnalysisRunRef,
  ExecutionFields,
  ExecutionRow,
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

  const fetchExecutionRow = (executionId: number, rowIndex: number) =>
    $api<ExecutionRow>(`/executions/${executionId}/rows/${rowIndex}`)

  return {
    createAnalysis,
    updateAnalysis,
    deleteAnalysis,
    fetchResults,
    computeAnalysis,
    fetchExecutionFields,
    fetchExecutionRow,
  }
}

/** Error message from a FastAPI error response, if any. */
export function apiErrorMessage(error: unknown): string | undefined {
  const detail = (error as { data?: { detail?: unknown } })?.data?.detail
  return typeof detail === 'string' ? detail : undefined
}
