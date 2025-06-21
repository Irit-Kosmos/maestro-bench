// Core types for the MAESTRO experiment system with complete traceability

export interface Model {
  id: number
  name: string
  provider: string
  description: string | null
  max_tokens: number | null
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
  model_id: number | null
  temperature: number | null
  max_tokens: number | null
  is_active: boolean
  is_default: boolean
  notes: string | null
  created_at: string
  prompt?: Prompt
  model?: Model
}

export interface Dataset {
  id: number
  name: string
  description: string
  created_at: string
  file_path?: string
}

export interface AgentConfig {
  id: number
  agent_id: string
  prompt_version: string
  active: boolean
  experiment_id?: number
}

export interface Experiment {
  id: number
  name: string
  description?: string
  dataset_id: number
  created_at: string
  completed_at?: string
  dataset?: Dataset
  agent_configs?: AgentConfig[]
  status?: ExperimentStatus
  results?: ExperimentResults
  executions?: ExperimentExecution[]
}

export type ExperimentStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface ExperimentResults {
  total_questions?: number
  processing_time?: number
}

export interface ExperimentStats {
  total: number
  completed: number
  running: number
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
  agent_executions: AgentExecutionConfig[]
}

export interface AgentExecutionConfig {
  id: number
  agent_id: number
  agent_name_snapshot: string
  agent_team_id_snapshot: number
  agent_team_name_snapshot: string
  final_system_prompt?: string
  final_user_prompt?: string
  final_variables?: string
  created_at: string
}

export interface ExperimentTrace {
  execution: ExperimentExecution
  agent_configs: AgentExecutionConfig[]
  experiment_metadata: Record<string, any>
  dataset_metadata: Record<string, any>
  results_summary: Record<string, any> // Summary from MAESTRO results file
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
  dataset_id: number | null | undefined
  agent_teams: string[]
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
  default_prompt_version_id?: number
  default_model_id?: number
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
  created_at: string
  agent?: Agent
  prompt_version?: PromptVersion
  model?: Model
}
