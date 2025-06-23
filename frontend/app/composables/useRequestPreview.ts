import type { Agent, AgentTeam } from '~/types'

/**
 * Composable for generating MAESTRO request preview
 */
export function useRequestPreview() {
  const { models } = useModels()
  const { allPromptVersions } = usePrompts()
  const { preview: datasetPreview } = useDatasetPreview()

  // Generate preview of the MAESTRO request
  const generatePreviewRequest = (
    selectedDataset: Ref<number | undefined>,
    requestConfig: Ref<{ columnMappings: Array<any> }>,
    selectedTeam: ComputedRef<AgentTeam>,
    agentConfigurations: Ref<Record<number, any>>,
  ) => {
    return computed(() => {
      if (!selectedDataset.value || requestConfig.value.columnMappings.length === 0) {
        return 'Select a dataset and configure column mappings to see the request preview'
      }

      const sampleData = datasetPreview.value?.sample_data?.[0] || {}

      // Build data object from column mappings
      const data: Record<string, any> = {}
      requestConfig.value.columnMappings.forEach((mapping) => {
        data[mapping.targetField] = sampleData[mapping.sourceColumn] || `[${mapping.sourceColumn} from dataset]`
      })

      const request = {
        data,
        config: {
          agents: selectedTeam.value?.agents
            .filter((agent: Agent) => agentConfigurations.value[agent.id]?.is_active !== false)
            .map((agent: Agent) => {
              const config = agentConfigurations.value[agent.id]
              const model = config?.model_id ? models.value?.find(m => m.id === config.model_id) : null
              const promptVersion = config?.prompt_version_id ? allPromptVersions.value?.find(v => v.id === config.prompt_version_id) : null

              return {
                agent_team_name: selectedTeam.value.name, 
                agent_name: agent.name,
                model: model?.name,
                temperature: config?.temperature ?? model?.default_temperature,
                max_tokens: config?.max_tokens,
                system_prompt: promptVersion?.system_prompt,
                user_prompt: promptVersion?.user_prompt,
                variables: promptVersion?.variables || {},
              }
            }) || [],
        },
      }

      return JSON.stringify(request, null, 2)
    })
  }

  return {
    generatePreviewRequest,
  }
}
