// Core types for the MAESTRO experiment system

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
  dataset_id: number
  created_at: string
  dataset?: Dataset
  agent_configs?: AgentConfig[]
  status?: ExperimentStatus
  results?: ExperimentResults
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

export interface Agent {
  id: number
  name: string
  description: string | null
  system_prompt: string | null
  user_prompt: string | null
  variables: string | null
  team_id: number
  created_at: string
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
  dataset_id: number | null
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
  system_prompt: string
  user_prompt: string
  variables?: string
  team_id: number
}
