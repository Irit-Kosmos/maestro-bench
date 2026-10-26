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

/** The palette tags choose from (see `TAG_COLORS` in utils/tags.ts) */
export type TagColor = 'red' | 'orange' | 'amber' | 'green' | 'teal' | 'blue' | 'indigo' | 'purple' | 'pink' | 'gray'

/** A label shared by every kind of item that can be tagged */
export interface Tag {
  id: number
  name: string
  color: TagColor
}

export interface Prompt {
  id: number
  name: string
  description: string | null
  tags: Tag[]
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
  description: string | null
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
  /** Step whose output is read ("12", or "12#2" for the second run of agent 12): see utils/steps */
  sourceStep?: string
  /** Mappings saved before agents could run twice name an agent only: it stands for its first step */
  sourceAgentId?: number
  sourceOutput?: string
  /** Dotted path into the agent's JSON output (`score`, `eval.score`); empty reads the whole output */
  sourcePath?: string
  staticValue?: string
}

/** "llm" calls a model with a prompt; "aggregator" computes formulas from other agents' outputs */
export type AgentKind = 'llm' | 'aggregator'

/** One named output of an aggregator */
export interface FormulaOutput {
  name: string
  formula: string
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
  /** Aggregators only */
  formulas?: FormulaOutput[]
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
  // Seed of the random sample: runs with the same seed take the same rows (the batch's seed, in a batch)
  sampling_seed?: number | null

  // Dataset rows processed by the latest execution that has results
  row_count?: number | null

  // Executions of the experiment: how many, and the figures of the latest one
  execution_count?: number
  // Status of each execution, from the newest to the oldest
  execution_statuses?: string[]
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
export type ExperimentStatus = 'pending' | 'queued' | 'running' | 'completed' | 'failed' | 'cancelled' | 'interrupted' | 'partial'

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
  /** null once the agent has been deleted: the snapshot keeps its name */
  agent_id: number | null
  /** The step of the experiment it ran ("12", "12#2"…); null only on an old snapshot of a deleted agent */
  step_key?: string | null
  /** Aggregator snapshots have empty model and prompt fields */
  kind?: AgentKind
  agent_name_snapshot: string
  model_name_snapshot: string
  model_provider_snapshot: string
  prompt_name_snapshot: string
  prompt_version_snapshot: string
  prompt_id?: number | null
  prompt_version_id?: number | null
  final_system_prompt?: string
  final_user_prompt?: string
  final_variables?: string
  final_input_mappings?: string
  /** JSON list of FormulaOutput, for aggregators */
  final_formulas?: string | null
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
  /** Whose credentials the workspace's calls use: its own key, the instance's, or none */
  source: 'workspace' | 'instance' | null
  /** The end of the workspace's own key, the only part ever shown */
  key_hint: string | null
  /** Whether the workspace may store its own key (a key provider, on an instance that can encrypt) */
  can_store_key: boolean
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
  models: { name: string, provider: string }[]
  row_count: number | null
  duration_seconds: number | null
  total_tokens: number | null
  total_cost_usd: number | null
}

/** What was run over a stretch of time */
export interface DashboardTotals {
  experiments: number
  /** Of those experiments, by how they ended */
  completed: number
  failed: number
  total_tokens: number
  total_cost_usd: number
  /** Rows the executions went through, the failed ones included */
  rows_done: number
  rows_failed: number
  /** Executions that failed, or went on with failed rows; the cancelled ones are not counted */
  executions_with_failures: number
}

/** The totals of one slice of the period, `start` being its first instant */
export interface DashboardBucket extends DashboardTotals {
  start: string
}

export interface DashboardActiveExperiment {
  id: number
  name: string
  status: ExperimentStatus
}

export type DashboardRange = '24h' | '7d' | '30d' | '90d' | 'all'

export interface DashboardActivity {
  range: DashboardRange
  /** First instant of the period; null for "all" */
  since: string | null
  current: DashboardTotals
  /** The stretch of the same length right before; null for "all", which has no before */
  previous: DashboardTotals | null
  /** The period cut in even slices, oldest first */
  buckets: DashboardBucket[]
  /** Experiments pending or running right now, newest first */
  active: DashboardActiveExperiment[]
}

export interface Dashboard {
  activity: DashboardActivity
  recent_experiments: DashboardExperiment[]
}

export interface Agent {
  id: number
  name: string
  description: string | null
  kind?: AgentKind
  default_prompt_version_id: number | null
  default_model_id: number | null
  created_at: string
  default_prompt_version?: PromptVersion
  default_model?: Model
  /** Only the agents list reads them */
  tags?: Tag[]
}

export interface CreateExperimentForm {
  name: string
  description?: string
  dataset_id: number | null | undefined
  /** Settings of each step, by step key */
  agent_configurations?: Record<string, {
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
  sampling_seed?: number // Seed of a random sample; drawn at random when left out
}

export interface CreateDatasetForm {
  name: string
  description: string
  /** The CSV or JSON file to upload */
  file: File
}

export interface CreateAgentForm {
  name: string
  description: string
  kind?: AgentKind
  default_prompt_version_id?: number | null
  default_model_id?: number | null
  tag_ids?: number[]
}

export interface ExperimentAgentConfig {
  id: number
  experiment_id: number
  agent_id: number
  /** The step this configures: "12", or "12#2" for the second run of agent 12 */
  step_key: string
  /** The step's name when it is not its agent's ("Corrector #2") */
  label?: string | null
  prompt_version_id: number | null
  model_id: number | null
  temperature: number | null
  max_tokens: number | null
  execution_order: number
  is_active: boolean
  input_mappings?: AgentInputMapping[] | null
  formulas?: FormulaOutput[] | null
  created_at: string
  agent?: Agent
  prompt_version?: PromptVersion
  model?: Model
}

/** How much several columns of a dataset agree on the same rows */
export interface DatasetAgreement {
  value_type: AnalysisValueType
  n_rows: number
  metrics: { key: string, label: string, description: string }[]
  columns: { column: string, n: number, n_missing: number, mean: number | null }[]
  pairs: {
    a: string
    b: string
    n: number
    metrics: Record<string, { value: number | null, undefined_reason: string | null }>
  }[]
  overall: {
    n_items: number
    unanimous: number | null
    alpha: { value: number | null, undefined_reason: string | null }
  }
  warnings: string[]
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
  tags: Tag[]
  created_at: string
  updated_at: string
}

export interface AnalysisForm {
  name: string
  description?: string | null
  config: AnalysisConfig
  runs: AnalysisRunRef[]
  tag_ids: number[]
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
  confusion?: { labels: string[], matrix: number[][], rows?: number[][][] } | null
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
  /** Aggregators also carry the value each formula variable resolved to */
  agents: { name: string | null, kind?: AgentKind, inputs?: Record<string, unknown> | null, output: unknown, error: string | null }[]
  error: string | null
}

/** One execution in the list spanning every experiment */
export interface ExecutionListItem {
  id: number
  experiment_id: number
  experiment_name: string
  batch_id: number | null
  batch_name: string | null
  dataset_name: string | null
  status: string
  started_at: string
  completed_at: string | null
  duration_seconds: number | null
  /** Live progress, in dataset rows; failed rows are counted in the rows done */
  rows_total: number | null
  rows_done: number
  rows_failed: number
  /** Dataset rows processed; null until the results file exists */
  row_count: number | null
  has_results: boolean
  total_tokens: number | null
  total_cost_usd: number | null
  /** In the order they ran */
  /** agent_id is null once the agent has been deleted */
  agents: { agent_id: number | null, kind?: AgentKind, name: string, model: string, provider: string, prompt: string, prompt_version: string }[]
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
  step_key: string
  field: VariationField
  /** A temperature of null is the model's own default */
  values: (number | null)[]
}

/** One axis as edited in the form: only what is added to the base configuration's value */
export interface VariationDraft {
  step_key: string
  field: VariationField
  extras: number[]
}

export interface BatchVariationValue {
  value: number | null
  label: string
}

export interface BatchVariation {
  step_key: string
  agent_id: number
  /** Name of the step: its agent's, then "name #2"… */
  agent_name: string
  field: VariationField
  values: BatchVariationValue[]
}

export interface BatchCoordinate {
  step_key: string
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
  // Status of each execution, from the newest to the oldest
  execution_statuses: string[]
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
  // Status of the executions that are not the latest of their experiment, from the newest to the oldest
  earlier_execution_statuses: string[]
  total_tokens: number | null
  total_cost_usd: number | null
  experiments: BatchExperiment[]
}

/** The signed-in user, as `/auth/me` describes them */
export interface AuthUser {
  id: number
  display_name: string
  email: string | null
  avatar_url: string | null
  is_instance_admin: boolean
}

export interface AuthProvider {
  name: string
  label: string
}

/** A workspace the signed-in user belongs to, with their role in it */
export interface Workspace {
  slug: string
  name: string
  role: 'viewer' | 'editor' | 'owner'
  archived: boolean
}

export type WorkspaceRole = Workspace['role']

/** What a public link can point to */
export type ShareKind = 'experiment' | 'batch' | 'analysis' | 'study'

/** The public read-only link of an item: whoever has the token can read the item */
export interface Share {
  id: number
  kind: ShareKind
  item_id: number
  token: string
  created_at: string
}

export interface WorkspaceMember {
  user_id: number
  display_name: string
  email: string | null
  avatar_url: string | null
  role: WorkspaceRole
  joined_at: string
}

export interface WorkspaceInvitation {
  id: number
  role: WorkspaceRole
  created_at: string
  /** null: the link works until it is revoked */
  expires_at: string | null
  /** People who joined through the link */
  uses: number
}

/** Returned once, when the invitation is made: the token is not kept anywhere */
export interface CreatedInvitation extends WorkspaceInvitation {
  token: string
}

export interface InvitationPreview {
  workspace_name: string
  role: WorkspaceRole
  invited_by: string | null
}

export interface AcceptedInvitation {
  slug: string
  name: string
  role: WorkspaceRole
  joined: boolean
}

// What a workspace has set up on the way to a first run (the getting-started checklist)
export interface SetupProgress {
  provider: boolean
  dataset: boolean
  prompt: boolean
  model: boolean
  agent: boolean
  experiment: boolean
}

// --- Studies and notes ---

/** What a study can gather */
export type StudyKind = 'experiment' | 'batch' | 'analysis'
/** What a note can be about: a study too */
export type NoteKind = StudyKind | 'study'
export type StudyStatus = 'active' | 'concluded' | 'archived'

export interface Person {
  id: number
  display_name: string
  avatar_url: string | null
}

export interface Study {
  id: number
  name: string
  /** Markdown */
  description: string | null
  status: StudyStatus
  tags: Tag[]
  author: Person | null
  /** What was put in the study: a batch is one item, not its experiments */
  counts: { experiments: number, batches: number, analyses: number }
  // Over the study's experiments, those of its batches included, each counted once
  execution_count: number
  total_tokens: number | null
  total_cost_usd: number | null
  created_at: string
  updated_at: string
}

export interface StudyItem {
  kind: StudyKind
  item_id: number
  name: string
  /** An experiment's status, a batch's overall status; an analysis has none */
  status: string | null
  dataset_name: string | null
  /** Experiments of a batch */
  experiment_count: number | null
  execution_count: number
  total_tokens: number | null
  total_cost_usd: number | null
  created_at: string
  added_at: string
  added_by: Person | null
}

export interface StudyDetail extends Study {
  /** Most recently added first */
  items: StudyItem[]
}

/** Which study an item of a kind is in */
export interface StudyMembership {
  study_id: number
  item_id: number
}

export interface Note {
  id: number
  kind: NoteKind
  item_id: number
  /** Markdown */
  body: string
  author: Person | null
  created_at: string
  updated_at: string
  can_edit: boolean
  can_delete: boolean
}

export interface StudyActivityEvent {
  type: 'note' | 'item_added' | 'experiment_completed'
  at: string
  actor: Person | null
  item: { kind: NoteKind, item_id: number, name: string } | null
  note: Note | null
}
