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

import type { Agent, AgentConfiguration, AgentInputMapping, CreateExperimentForm, PromptVersion } from '~/types'

interface ExperimentDetails {
  name: string
  description: string
}

interface SamplingConfig {
  sampling_type: string
  sampling_size?: number
  sampling_start_row?: number
  sampling_end_row?: number
  sampling_seed?: number
}

/**
 * Composable for managing experiment form state and validation
 */
export function useExperimentForm(
  agents?: Ref<readonly Agent[] | null | undefined>,
  allPromptVersions?: Ref<PromptVersion[] | null | undefined>,
) {
  // Form state
  const formData = ref<CreateExperimentForm>({
    name: '',
    dataset_id: undefined,
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
    sampling_seed: undefined,
  })

  // Settings of each step of the pipeline, by step key (see utils/steps)
  const agentConfigurations = ref<Record<string, AgentConfiguration>>({})

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

  // Get variables required by a step's selected prompt version
  function getAgentPromptVariables(key: string): string[] {
    const config = agentConfigurations.value[key]
    if (!config?.prompt_version_id)
      return []
    const version = allPromptVersions?.value?.find(v => v.id === config.prompt_version_id)
    return parsePromptVariables(version?.variables)
  }

  // Get active step keys (excluding explicitly disabled steps)
  function getActiveStepKeys(): string[] {
    return Object.entries(agentConfigurations.value)
      .filter(([_, config]) => config?.is_active !== false)
      .map(([key]) => key)
  }

  function isAggregator(key: string): boolean {
    const agentId = agentIdOfStep(key)
    return !!agents?.value?.some(a => a.id === agentId && a.kind === 'aggregator')
  }

  // The backend silently skips a step without a prompt version or a model, so an experiment
  // is only valid when every active step has both and maps every variable of its prompt.
  // An aggregator needs its formulas written and their variables mapped (the backend checks the rest).
  function areAgentsReady(): boolean {
    const activeKeys = getActiveStepKeys()
    if (activeKeys.length === 0)
      return false

    return activeKeys.every((key) => {
      const config = agentConfigurations.value[key]
      if (isAggregator(key))
        return aggregatorIssues(config).length === 0 && !formulaErrorsOf(config?.formulas)?.errors.some(Boolean)
      if (!config?.prompt_version_id || !config.model_id)
        return false

      const inputMappings = config.input_mappings || []
      return getAgentPromptVariables(key).every(variable =>
        inputMappings.some((m: AgentInputMapping) => m.variable === variable && isMappingComplete(m)),
      )
    })
  }

  const agentsValid = computed(() => areAgentsReady())

  const formValid = computed(() => detailsValid.value && datasetValid.value && agentsValid.value)

  // Helper to get active step configurations
  const getActiveAgentConfigurations = () => {
    return Object.fromEntries(
      Object.entries(agentConfigurations.value).filter(([_, config]) => config?.is_active === true),
    )
  }

  // Prepare experiment data for submission
  const prepareExperimentData = (options?: {
    executionOrder?: Map<string, number>
  }) => {
    const agent_configs = getActiveAgentConfigurations()

    // Add execution_order to each step config
    if (options?.executionOrder) {
      Object.keys(agent_configs).forEach((key) => {
        const order = options.executionOrder!.get(key)
        if (order !== undefined) {
          agent_configs[key] = {
            ...agent_configs[key],
            execution_order: order,
          }
        }
      })
    }

    return {
      name: experimentDetails.value.name.trim(),
      description: experimentDetails.value.description.trim() || undefined,
      dataset_id: formData.value.dataset_id!,
      agent_configurations: agent_configs,
      sampling_type: samplingConfig.value.sampling_type,
      sampling_size: samplingConfig.value.sampling_size,
      sampling_start_row: samplingConfig.value.sampling_start_row,
      sampling_end_row: samplingConfig.value.sampling_end_row,
      sampling_seed: samplingConfig.value.sampling_type === 'random' ? samplingConfig.value.sampling_seed : undefined,
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
