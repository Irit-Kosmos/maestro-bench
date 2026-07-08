<script setup lang="ts">
import type { AgentTeam, Model, PromptVersion } from '~/types'

interface Props {
  agentConfigurations: Record<number, any>
  agentTeams?: AgentTeam[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  datasetHeaders?: string[]
}

interface Emits {
  updateAgentConfig: [agentId: number, field: string, value: any]
  openPromptDetails: [promptVersionId: number]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Get agent management data from props
const agentTeams = computed(() => props.agentTeams || [])
const models = computed(() => props.models || [])
const allPromptVersions = computed(() => props.allPromptVersions || [])

// Ref for the flow view component (exposed to parent for computeExecutionOrder)
const flowViewRef = ref()

// Expose flow view ref so parent can call computeExecutionOrder
defineExpose({
  flowViewRef,
})

function updateAgentConfig(agentId: number, field: string, value: any) {
  emit('updateAgentConfig', agentId, field, value)
}

function openPromptDetails(promptVersionId: number) {
  emit('openPromptDetails', promptVersionId)
}
</script>

<template>
  <div class="space-y-6">
    <ExperimentsAgentFlowView
      ref="flowViewRef"
      :agent-teams="agentTeams"
      :models="models"
      :all-prompt-versions="allPromptVersions"
      :agent-configurations="agentConfigurations"
      :dataset-headers="datasetHeaders || []"
      @update-agent-config="updateAgentConfig"
      @open-prompt-details="openPromptDetails"
    />
  </div>
</template>
