// Core types for the MAESTRO-bench API

export interface Model {
  id: number
  name: string
  provider: string
  description: string | null
  max_tokens: number | null
  default_temperature: number | null
  default_max_tokens: number | null
  is_active: boolean
  created_at: string
}

export interface Prompt {
  id: number
  name: string
  description: string | null
  category: string | null
  created_at: string
  versions?: PromptVersion[]
}

export interface PromptVersion {
  id: number
  prompt_id: number
  version: string
  system_prompt: string | null
  user_prompt: string | null
  variables: string | null
  is_active: boolean
  is_default: boolean
  notes: string | null
  created_at: string
  prompt?: Prompt
}

export interface Dataset {
  id: number
  name: string
  description: string
  created_at: string
  file_path?: string
}

export interface DatasetStats {
  id: number
  name: string
  description: string
  file_path?: string
  created_at: string
  experiment_count: number
}

export interface AgentInputMapping {
  variable: string
  source: 'dataset' | 'agent' | 'static'
  sourceColumn?: string
  sourceAgentId?: number
  sourceOutput?: string
  staticValue?: string
}

// Per-agent settings chosen while creating an experiment
export interface AgentConfiguration {
  prompt_version_id?: number
  model_id?: number
  temperature?: number
  max_tokens?: number
  is_active?: boolean
  execution_order?: number
  input_mappings?: AgentInputMapping[]
}

export interface Experiment {
  id: number
  name: string
  description?: string
  dataset_id: number
  created_at: string
  completed_at?: string
  dataset?: Dataset
  agent_configs?: ExperimentAgentConfig[]
  status?: ExperimentStatus
  results?: ExperimentResults
  executions?: ExperimentExecution[]

  // Dataset sampling configuration
  sampling_type?: string
  sampling_size?: number
  sampling_start_row?: number
  sampling_end_row?: number

  // Dataset rows processed by the latest execution that has results
  row_count?: number | null

  // Executions of the experiment: how many, and the figures of the latest one
  execution_count?: number
  duration_seconds?: number | null
  rows_failed?: number | null
  total_tokens?: number | null
  total_cost_usd?: number | null

  // Batch the experiment belongs to, and its coordinates in the batch's grid ({ [agentId]: { [field]: value } })
  batch_id?: number | null
  batch_name?: string | null
  variant?: Record<string, Record<string, number>> | null

  // The agents' configuration, as submitted
  experiment_configs?: ExperimentAgentConfig[]
}

// 'partial' only exists for batches: some experiments completed, others did not
export type ExperimentStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled' | 'partial'

// Live state of an execution, as pushed by the /events stream (failed rows are counted in rows_done)
export interface RunState {
  experiment_id: number
  batch_id: number | null
  // null when the run failed before an execution was created
  execution_id: number | null
  status: string
  // null until the rows have been counted
  rows_total: number | null
  rows_done: number
  rows_failed: number
}

export interface ExperimentResults {
  total_questions?: number
  processing_time?: number
}

// New traceability types
export interface ExperimentExecution {
  id: number
  experiment_id: number
  started_at: string
  completed_at?: string
  status: string
  dataset_snapshot: string
  results_file_path?: string
  // Dataset rows processed; null until the results file exists
  row_count?: number | null
  // Aggregated metrics
  total_tokens?: number
  total_cost_usd?: number
  agent_executions: AgentExecutionSnapshot[]
}

export interface AgentExecutionSnapshot {
  id: number
  execution_id: number
  agent_id: number
  agent_name_snapshot: string
  agent_team_name_snapshot?: string
  model_name_snapshot: string
  model_provider_snapshot: string
  prompt_name_snapshot: string
  prompt_version_snapshot: string
  final_system_prompt?: string
  final_user_prompt?: string
  final_variables?: string
  final_input_mappings?: string
  final_temperature?: number
  final_max_tokens?: number
  execution_order: number
  created_at: string
}

export interface ProviderStatus {
  provider: string
  configured: boolean
  /** Environment variable the backend reads the key or URL from */
  env_var: string
  /** What that variable holds: an API key, or the URL of a self-hosted server that needs no key */
  kind: 'key' | 'url'
}

// Dashboard: recent runs with what their latest execution produced, and the last days' activity
export interface DashboardExperiment {
  id: number
  name: string
  status: ExperimentStatus
  created_at: string
  batch_id: number | null
  batch_name: string | null
  dataset_name: string | null
  /** Distinct models of the pipeline, in execution order */
  models: string[]
  row_count: number | null
  duration_seconds: number | null
  total_tokens: number | null
  total_cost_usd: number | null
}

export interface DashboardActivity {
  days: number
  experiments: number
  total_tokens: number
  total_cost_usd: number
  /** Experiments pending or running right now */
  active: number
}

export interface Dashboard {
  activity: DashboardActivity
  recent_experiments: DashboardExperiment[]
}

export interface Agent {
  id: number
  name: string
  description: string | null
  default_prompt_version_id: number | null
  default_model_id: number | null
  team_id: number
  created_at: string
  default_prompt_version?: PromptVersion
  default_model?: Model
}

export interface AgentTeam {
  id: number
  name: string
  description: string | null
  created_at: string
  agents: readonly Agent[]
}

export interface CreateExperimentForm {
  name: string
  description?: string
  dataset_id: number | null | undefined
  agent_teams: string[]
  agent_configurations?: Record<number, {
    prompt_version_id?: number
    model_id?: number
    temperature?: number
    max_tokens?: number
    is_active?: boolean
  }>

  // Dataset sampling configuration
  sampling_type?: string // 'all', 'random', 'range'
  sampling_size?: number // Number of rows for random sampling
  sampling_start_row?: number // Start row for range sampling (1-based)
  sampling_end_row?: number // End row for range sampling (1-based, inclusive)
}

export interface CreateDatasetForm {
  name: string
  description: string
  file_path?: string
}

export interface CreateAgentTeamForm {
  name: string
  description: string
  agent_ids?: number[]
}

export interface CreateAgentForm {
  name: string
  description: string
  default_prompt_version_id?: number | null
  default_model_id?: number | null
  team_id: number
}

export interface ExperimentAgentConfig {
  id: number
  experiment_id: number
  agent_id: number
  prompt_version_id: number
  model_id: number
  temperature: number | null
  max_tokens: number | null
  execution_order: number
  is_active: boolean
  input_mappings?: AgentInputMapping[] | null
  created_at: string
  agent?: Agent
  prompt_version?: PromptVersion
  model?: Model
}

// Analyses
export type AnalysisValueType = 'numeric' | 'categorical'

export interface AnalysisConfig {
  truth_column: string
  output_path: string
  value_type: AnalysisValueType
  metrics: string[]
  ignore_case: boolean
  n_boot: number
  confidence: number
  seed: number
}

export interface AnalysisRunRef {
  execution_id: number
  agent_name: string
  label?: string | null
}

export interface Analysis {
  id: number
  name: string
  description?: string | null
  config: AnalysisConfig
  runs: AnalysisRunRef[]
  created_at: string
  updated_at: string
}

export interface AnalysisForm {
  name: string
  description?: string | null
  config: AnalysisConfig
  runs: AnalysisRunRef[]
}

export interface MetricInfo {
  key: string
  label: string
  kind: AnalysisValueType
  description: string
  lower_is_better: boolean
}

export interface MetricValue {
  value: number | null
  ci_low: number | null
  ci_high: number | null
  undefined_reason: string | null
}

export interface ExcludedRow {
  row_index: number | null
  dataset_row_id: number | null
  reason: string
}

export interface AnalysisRunResult {
  execution_id: number
  agent_name: string
  label: string
  status: 'ok' | 'missing' | 'unavailable'
  error?: string | null
  experiment_id?: number | null
  experiment_name?: string | null
  n_valid: number
  n_total: number
  coverage: number | null
  metrics: Record<string, MetricValue>
  exclusions: Record<string, number>
  excluded_rows: ExcludedRow[]
  warnings: string[]
  points?: { pred: number, truth: number, row_index: number | null }[] | null
  confusion?: { labels: string[], matrix: number[][] } | null
}

export interface AnalysisResult {
  metrics: MetricInfo[]
  runs: AnalysisRunResult[]
  warnings: string[]
}

export interface ExecutionFields {
  execution_id: number
  columns: string[]
  agents: { name: string, model: string | null, execution_order: number, paths: string[] }[]
}

/** One dataset row of an execution: what went in, what each agent returned */
export interface ExecutionRow {
  row_index: number
  input_data: Record<string, unknown>
  agents: { name: string | null, output: unknown, error: string | null }[]
  error: string | null
}

export interface AvailableExecution {
  execution_id: number
  experiment_id: number
  experiment_name: string
  dataset_name: string | null
  started_at: string
  completed_at: string | null
  row_count: number | null
  agents: { name: string, model: string }[]
}

// --- Batches: experiments generated from one base configuration by varying agent fields ---

export type VariationField = 'model_id' | 'prompt_version_id' | 'temperature'

/** One axis of a batch's grid, as submitted: every value that runs, the base configuration's included */
export interface Variation {
  agent_id: number
  field: VariationField
  /** A temperature of null is the model's own default */
  values: (number | null)[]
}

/** One axis as edited in the form: only what is added to the base configuration's value */
export interface VariationDraft {
  agent_id: number
  field: VariationField
  extras: number[]
}

export interface BatchVariationValue {
  value: number | null
  label: string
}

export interface BatchVariation {
  agent_id: number
  agent_name: string
  field: VariationField
  values: BatchVariationValue[]
}

export interface BatchCoordinate {
  agent_id: number
  field: VariationField
  value: number | null
  label: string
}

export interface BatchExperiment {
  id: number
  name: string
  status: ExperimentStatus
  coordinates: BatchCoordinate[]
  created_at: string
  execution_id: number | null
  execution_status: string | null
  // Latest execution that completed, which is not always the latest one
  last_completed_execution_id: number | null
  started_at: string | null
  completed_at: string | null
  duration_seconds: number | null
  row_count: number | null
  // Executions of the experiment; the figures are those of the latest one
  execution_count: number
  rows_failed: number | null
  total_tokens: number | null
  total_cost_usd: number | null
  agent_names: string[]
}

export interface Batch {
  id: number
  name: string
  description: string | null
  created_at: string
  base_experiment_id: number | null
  base_experiment_name: string | null
  dataset_id: number | null
  dataset_name: string | null
  variations: BatchVariation[]
  status: ExperimentStatus
  counts: Record<string, number>
  // Executions of all the experiments; tokens and cost add up the latest one of each
  execution_count: number
  total_tokens: number | null
  total_cost_usd: number | null
  experiments: BatchExperiment[]
}
