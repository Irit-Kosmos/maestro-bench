/**
 * Composable for managing agent configuration in the experiment form.
 */
export function useAgentManagement() {
  // Update a single field of an agent's configuration
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
    updateAgentConfiguration,
  }
}
