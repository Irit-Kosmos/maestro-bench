import type { CreateExperimentForm } from '~/types'

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

interface RequestConfig {
  columnMappings: Array<{
    id: string
    sourceColumn: string
    targetField: string
  }>
}

interface AgentConfiguration {
  prompt_version_id?: number
  model_id?: number
  temperature?: number
  max_tokens?: number
  is_active?: boolean
}

/**
 * Composable for managing experiment form state and validation
 */
export function useExperimentForm() {
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

  const requestConfig = ref<RequestConfig>({
    columnMappings: [],
  })

  const selectedTeamId = ref<number | null>(null)
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
          return formData.value.dataset_id != null
        case 2:
          // Sampling step validation
          if (samplingConfig.value.sampling_type === 'random') {
            return samplingConfig.value.sampling_size && samplingConfig.value.sampling_size > 0
          }
          if (samplingConfig.value.sampling_type === 'range') {
            return samplingConfig.value.sampling_start_row
              && samplingConfig.value.sampling_end_row
              && samplingConfig.value.sampling_start_row <= samplingConfig.value.sampling_end_row
          }
          return true // 'all' option is always valid
        case 3:
          return selectedTeamId.value != null
        case 4:
          // Request configuration step validation - at least one column mapping required
          return requestConfig.value.columnMappings.length > 0
            && requestConfig.value.columnMappings.every(mapping =>
              mapping.sourceColumn && mapping.targetField.trim(),
            )
        default:
          return false
      }
    }
  })

  const formValid = computed(() => {
    return experimentDetails.value.name.trim()
      && formData.value.dataset_id != null
      && selectedTeamId.value != null
      && requestConfig.value.columnMappings.length > 0
      && requestConfig.value.columnMappings.every(mapping =>
        mapping.sourceColumn && mapping.targetField.trim(),
      )
  })

  // Helper to get active agent configurations
  const getActiveAgentConfigurations = () => {
    return Object.fromEntries(
      Object.entries(agentConfigurations.value).filter(([_, config]) => config.is_active !== false),
    )
  }

  // Prepare experiment data for submission
  const prepareExperimentData = () => {
    return {
      name: experimentDetails.value.name.trim(),
      description: experimentDetails.value.description.trim() || undefined,
      dataset_id: formData.value.dataset_id!,
      agent_teams: formData.value.agent_teams,
      agent_configurations: getActiveAgentConfigurations(),
      sampling_type: samplingConfig.value.sampling_type,
      sampling_size: samplingConfig.value.sampling_size,
      sampling_start_row: samplingConfig.value.sampling_start_row,
      sampling_end_row: samplingConfig.value.sampling_end_row,
      column_mappings: requestConfig.value.columnMappings,
    }
  }

  return {
    // State
    formData,
    experimentDetails,
    samplingConfig,
    requestConfig,
    selectedTeamId,
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
