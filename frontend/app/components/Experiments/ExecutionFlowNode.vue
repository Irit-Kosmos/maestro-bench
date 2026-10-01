<script setup lang="ts">
import type { AgentExecutionSnapshot } from '~/types'

export interface ExecutionFlowNodeData {
  snapshot: AgentExecutionSnapshot
}

const props = defineProps<{
  id: string
  data: ExecutionFlowNodeData
  selected?: boolean
}>()

const snapshot = computed(() => props.data?.snapshot)

const agentName = computed(() => snapshot.value?.agent_name_snapshot || 'Unknown Agent')
const teamName = computed(() => snapshot.value?.agent_team_name_snapshot)
const isSelected = computed(() => props.selected || false)

const promptDisplay = computed(() => {
  const name = snapshot.value?.prompt_name_snapshot
  const version = snapshot.value?.prompt_version_snapshot
  if (!name)
    return 'No prompt'
  return version ? `${name} v${version}` : name
})

const modelDisplay = computed(() => {
  const name = snapshot.value?.model_name_snapshot
  const provider = snapshot.value?.model_provider_snapshot
  if (!name)
    return 'No model'
  return provider ? `${name} (${provider})` : name
})

const promptVariables = computed<string[]>(() => {
  const variablesJson = snapshot.value?.final_variables
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
})

const inputMappings = computed(() => {
  const mappingsJson = snapshot.value?.final_input_mappings
  if (!mappingsJson)
    return []
  try {
    const parsed = JSON.parse(mappingsJson)
    return Array.isArray(parsed) ? parsed : []
  }
  catch {
    return []
  }
})

function getVariableSourceLabel(variable: string): string {
  const mapping = inputMappings.value.find(m => m.variable === variable)
  if (!mapping)
    return 'unset'
  switch (mapping.source) {
    case 'dataset':
      return mapping.sourceColumn || 'dataset'
    case 'agent':
      return mapping.sourceAgentId ? `agent #${mapping.sourceAgentId}` : 'agent'
    case 'static':
      return 'static'
    default:
      return mapping.source
  }
}

function getVariableSourceColor(variable: string): 'neutral' | 'info' | 'warning' | 'success' {
  const mapping = inputMappings.value.find(m => m.variable === variable)
  if (!mapping)
    return 'neutral'
  switch (mapping.source) {
    case 'dataset':
      return 'info'
    case 'agent':
      return 'warning'
    case 'static':
      return 'success'
    default:
      return 'neutral'
  }
}
</script>

<template>
  <div
    class="execution-flow-node rounded-lg border-2 transition-[border-color,box-shadow,opacity] duration-150 min-w-[200px]"
    :class="{
      'border-primary-500 bg-white shadow-lg': isSelected,
      'border-neutral-200 bg-white shadow-sm': !isSelected,
    }"
  >
    <!-- Target handle (left side - incoming connection) -->
    <VueFlowHandle
      type="target"
      position="left"
      class="!w-3 !h-3 !bg-primary-500 !border-2 !border-white"
    />

    <!-- Node content -->
    <div class="p-3">
      <!-- Header -->
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0 flex-1">
          <div class="font-medium text-sm text-neutral-900 truncate">
            {{ agentName }}
          </div>
          <div v-if="teamName" class="text-xs text-neutral-500 truncate mt-0.5">
            {{ teamName }}
          </div>
        </div>
        <div class="w-2 h-2 rounded-full flex-shrink-0 mt-1.5 bg-green-500" />
      </div>

      <!-- Config summary -->
      <div class="mt-2 pt-2 border-t border-neutral-100 space-y-1.5">
        <div class="flex items-center gap-1 text-xs text-neutral-500">
          <UIcon name="i-lucide-message-square" class="w-3 h-3 flex-shrink-0" />
          <span class="truncate" :title="promptDisplay">
            {{ promptDisplay }}
          </span>
        </div>
        <div class="flex items-center gap-1 text-xs text-neutral-500">
          <UIcon name="i-lucide-brain-circuit" class="w-3 h-3 flex-shrink-0" />
          <span class="truncate" :title="modelDisplay">
            {{ modelDisplay }}
          </span>
        </div>

        <!-- Input variables -->
        <div v-if="promptVariables.length > 0" class="flex flex-wrap gap-1 pt-1">
          <UTooltip
            v-for="variable in promptVariables"
            :key="variable"
            :text="getVariableSourceLabel(variable)"
          >
            <UBadge
              size="xs"
              :color="getVariableSourceColor(variable)"
              variant="subtle"
              class="font-mono"
            >
              {{ variable }}
            </UBadge>
          </UTooltip>
        </div>
      </div>
    </div>

    <!-- Source handle (right side - outgoing connection) -->
    <VueFlowHandle
      type="source"
      position="right"
      class="!w-3 !h-3 !bg-primary-500 !border-2 !border-white"
    />
  </div>
</template>

<style scoped>
.execution-flow-node {
  /* Prevent text selection during drag */
  user-select: none;
}
</style>
