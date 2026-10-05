import type { AgentConfiguration, AgentInputMapping, AgentTeam, CreateExperimentForm, PromptVersion } from '~/types'

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

  // Validity of each section of the form
  const detailsValid = computed(() => experimentDetails.value.name.trim().length > 0)

  const datasetValid = computed(() => {
    if (formData.value.dataset_id == null)
      return false
    const { sampling_type, sampling_size, sampling_start_row, sampling_end_row } = samplingConfig.value
    if (sampling_type === 'random')
      return !!sampling_size && sampling_size > 0
    if (sampling_type === 'range')
      return !!sampling_start_row && !!sampling_end_row && sampling_start_row <= sampling_end_row
    return true // 'all' is always valid
  })

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

  function isAggregator(agentId: number): boolean {
    return !!agentTeams?.value?.some(team => team.agents?.some(a => a.id === agentId && a.kind === 'aggregator'))
  }

  // The backend silently skips an agent without a prompt version or a model, so an experiment
  // is only valid when every active agent has both and maps every variable of its prompt.
  // An aggregator needs its formulas written and their variables mapped (the backend checks the rest).
  function areAgentsReady(): boolean {
    const activeIds = getActiveAgentIds()
    if (activeIds.length === 0)
      return false

    return activeIds.every((agentId) => {
      const config = agentConfigurations.value[agentId]
      if (isAggregator(agentId))
        return aggregatorIssues(config).length === 0 && !formulaErrorsOf(config?.formulas)?.errors.some(Boolean)
      if (!config?.prompt_version_id || !config.model_id)
        return false

      const inputMappings = config.input_mappings || []
      return getAgentPromptVariables(agentId).every(variable =>
        inputMappings.some((m: AgentInputMapping) => m.variable === variable && isMappingComplete(m)),
      )
    })
  }

  const agentsValid = computed(() => areAgentsReady())

  const formValid = computed(() => detailsValid.value && datasetValid.value && agentsValid.value)

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
    detailsValid,
    datasetValid,
    agentsValid,
    formValid,

    // Methods
    prepareExperimentData,
  }
}
