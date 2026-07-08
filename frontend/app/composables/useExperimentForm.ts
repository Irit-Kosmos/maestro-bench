import type { AgentInputMapping, AgentTeam, CreateExperimentForm, PromptVersion } from '~/types'

interface ExperimentDetails {
  name: string
  description: string
}

interface SamplingConfig {
  sampling_type: string
  sampling_size?: number
  sampling_start_row?: number
  sampling_end_row?: number
}

interface AgentConfiguration {
  prompt_version_id?: number
  model_id?: number
  temperature?: number
  max_tokens?: number
  is_active?: boolean
  execution_order?: number
  input_mappings?: AgentInputMapping[]
}

/**
 * Composable for managing experiment form state and validation
 */
export function useExperimentForm(
  agentTeams?: Ref<AgentTeam[] | null | undefined>,
  allPromptVersions?: Ref<PromptVersion[] | null | undefined>,
) {
  // Form state
  const formData = ref<CreateExperimentForm>({
    name: '',
    dataset_id: undefined,
    agent_teams: [],
  })

  const experimentDetails = ref<ExperimentDetails>({
    name: '',
    description: '',
  })

  const samplingConfig = ref<SamplingConfig>({
    sampling_type: 'all',
    sampling_size: undefined,
    sampling_start_row: undefined,
    sampling_end_row: undefined,
  })

  const agentConfigurations = ref<Record<number, AgentConfiguration>>({})

  // Computed property to handle dataset selection conversion between null and undefined
  const selectedDataset = computed({
    get: () => formData.value.dataset_id ?? undefined,
    set: (value: number | undefined) => {
      formData.value.dataset_id = value ?? null
    },
  })

  // Step validation
  const isStepValid = computed(() => {
    return (step: number) => {
      switch (step) {
        case 0:
          return experimentDetails.value.name.trim().length > 0
        case 1:
          // Dataset step: a dataset must be selected and sampling config must be valid
          if (formData.value.dataset_id == null)
            return false
          if (samplingConfig.value.sampling_type === 'random') {
            return samplingConfig.value.sampling_size && samplingConfig.value.sampling_size > 0
          }
          if (samplingConfig.value.sampling_type === 'range') {
            return samplingConfig.value.sampling_start_row
              && samplingConfig.value.sampling_end_row
              && samplingConfig.value.sampling_start_row <= samplingConfig.value.sampling_end_row
          }
          return true // 'all' option is always valid
        case 2:
          // Agent configuration step validation: at least one active agent in the flow
          return Object.keys(agentConfigurations.value).length > 0
            && Object.values(agentConfigurations.value).some(config => config?.is_active !== false)
        default:
          return false
      }
    }
  })

  // Parse prompt version variables from JSON string to array
  function parsePromptVariables(variablesJson: string | null | undefined): string[] {
    if (!variablesJson)
      return []
    try {
      const parsed = JSON.parse(variablesJson)
      if (Array.isArray(parsed))
        return parsed
      if (typeof parsed === 'object' && parsed !== null)
        return Object.keys(parsed)
      return []
    }
    catch {
      return []
    }
  }

  // Get variables required by an agent's selected prompt version
  function getAgentPromptVariables(agentId: number): string[] {
    const config = agentConfigurations.value[agentId]
    if (!config?.prompt_version_id)
      return []
    const version = allPromptVersions?.value?.find(v => v.id === config.prompt_version_id)
    return parsePromptVariables(version?.variables)
  }

  // Get active agent IDs (excluding explicitly disabled agents)
  function getActiveAgentIds(): number[] {
    return Object.entries(agentConfigurations.value)
      .filter(([_, config]) => config?.is_active !== false)
      .map(([id]) => Number.parseInt(id))
  }

  // Check whether every variable of every active agent is mapped, either via global
  // column_mappings or per-agent input_mappings. Empty variable lists count as satisfied.
  function areAllVariablesMapped(): boolean {
    const activeIds = getActiveAgentIds()
    if (activeIds.length === 0)
      return false

    return activeIds.every((agentId) => {
      const variables = getAgentPromptVariables(agentId)
      if (variables.length === 0)
        return true

      const inputMappings = agentConfigurations.value[agentId]?.input_mappings || []
      return variables.every(variable =>
        inputMappings.some((m: AgentInputMapping) => m.variable === variable),
      )
    })
  }

  const formValid = computed(() => {
    const basicValid = experimentDetails.value.name.trim()
      && formData.value.dataset_id != null

    if (!basicValid)
      return false

    // Agent configuration validation: at least one active agent in the flow
    const agentValid = Object.keys(agentConfigurations.value).length > 0
      && Object.values(agentConfigurations.value).some(config => config?.is_active !== false)

    if (!agentValid)
      return false

    // Mapping validation: every prompt variable of every active agent must be mapped
    // via per-agent input_mappings in the node view.
    return areAllVariablesMapped()
  })

  // Helper to get active agent configurations
  const getActiveAgentConfigurations = () => {
    return Object.fromEntries(
      Object.entries(agentConfigurations.value).filter(([_, config]) => config?.is_active === true),
    )
  }

  // Prepare experiment data for submission
  const prepareExperimentData = (options?: {
    agentTeams?: any[]
    executionOrder?: Map<number, number>
  }) => {
    const agent_configs = getActiveAgentConfigurations()

    // Derive team IDs from agents in the flow
    let agent_teams = formData.value.agent_teams
    if (options?.agentTeams) {
      const activeAgentIds = Object.keys(agent_configs).map(Number)
      const teamIds = new Set<number>()
      options.agentTeams.forEach((team) => {
        team.agents?.forEach((agent: any) => {
          if (activeAgentIds.includes(agent.id)) {
            teamIds.add(team.id)
          }
        })
      })
      agent_teams = Array.from(teamIds).map(String)
    }

    // Add execution_order to each agent config
    if (options?.executionOrder) {
      Object.keys(agent_configs).forEach((key) => {
        const agentId = Number.parseInt(key)
        const order = options.executionOrder!.get(agentId)
        if (order !== undefined) {
          agent_configs[agentId] = {
            ...agent_configs[agentId],
            execution_order: order,
          }
        }
      })
    }

    return {
      name: experimentDetails.value.name.trim(),
      description: experimentDetails.value.description.trim() || undefined,
      dataset_id: formData.value.dataset_id!,
      agent_teams,
      agent_configurations: agent_configs,
      sampling_type: samplingConfig.value.sampling_type,
      sampling_size: samplingConfig.value.sampling_size,
      sampling_start_row: samplingConfig.value.sampling_start_row,
      sampling_end_row: samplingConfig.value.sampling_end_row,
      column_mappings: [],
    }
  }

  return {
    // State
    formData,
    experimentDetails,
    samplingConfig,
    agentConfigurations,
    selectedDataset,

    // Computed
    isStepValid,
    formValid,

    // Methods
    getActiveAgentConfigurations,
    prepareExperimentData,
  }
}
