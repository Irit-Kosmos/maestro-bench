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
}

export type ExperimentStatus = 'pending' | 'running' | 'completed' | 'failed'

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
