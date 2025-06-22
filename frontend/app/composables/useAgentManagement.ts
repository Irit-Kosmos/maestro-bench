/**
 * Composable for managing agent team selection and configuration
 */
export function useAgentManagement() {
  const { agentTeams } = useAgentTeams()
  const { allPromptVersions } = usePrompts()
  const { models } = useModels()

  // Get full teams data with agents
  const fullTeams = computed(() => agentTeams.value || [])

  // Get selected team
  const getSelectedTeam = (selectedTeamId: Ref<number | null>) => {
    return computed(() => {
      return selectedTeamId.value ? fullTeams.value.find(team => team.id === selectedTeamId.value) : null
    })
  }

  // Get available prompt versions for dropdowns
  const promptVersionOptions = computed(() => {
    const options: Array<{ label: string, value: number }> = []

    allPromptVersions.value?.forEach((version) => {
      if (version.is_active) {
        options.push({
          label: `${version.prompt?.name || 'Unknown'} v${version.version}${version.is_default ? ' (Default)' : ''}`,
          value: version.id,
        })
      }
    })

    return options
  })

  const modelOptions = computed(() => {
    return models.value?.filter(model => model.is_active).map(model => ({
      label: `${model.name} (${model.provider})`,
      value: model.id,
    })) || []
  })

  // Select team and initialize configurations
  const selectTeam = (
    teamId: number,
    selectedTeamId: Ref<number | null>,
    formData: Ref<any>,
    agentConfigurations: Ref<Record<number, any>>,
  ) => {
    // Clear previous selection
    if (selectedTeamId.value !== null) {
      const previousTeam = fullTeams.value.find(t => t.id === selectedTeamId.value)
      if (previousTeam) {
        previousTeam.agents.forEach((agent) => {
          delete agentConfigurations.value[agent.id]
        })
      }
    }

    // Set new selection
    selectedTeamId.value = teamId
    formData.value.agent_teams = [teamId.toString()]

    // Initialize configurations for new team with default values
    const team = fullTeams.value.find(t => t.id === teamId)
    if (team) {
      team.agents.forEach((agent) => {
        agentConfigurations.value[agent.id] = {
          prompt_version_id: agent.default_prompt_version_id || undefined,
          model_id: agent.default_model_id || undefined,
          temperature: undefined, // Will use model default
          max_tokens: undefined, // Will use model default
          is_active: true,
        }
      })
    }
  }

  // Update agent configuration
  const updateAgentConfiguration = (
    agentId: number,
    field: string,
    value: any,
    agentConfigurations: Ref<Record<number, any>>,
  ) => {
    if (!agentConfigurations.value[agentId]) {
      agentConfigurations.value[agentId] = {}
    }
    agentConfigurations.value[agentId][field as keyof typeof agentConfigurations.value[number]] = value
  }

  return {
    // Computed
    fullTeams,
    promptVersionOptions,
    modelOptions,

    // Methods
    getSelectedTeam,
    selectTeam,
    updateAgentConfiguration,

    // Composables
    allPromptVersions,
    models,
  }
}
