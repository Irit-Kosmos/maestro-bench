<script setup lang="ts">
import type { AgentFlowNodeData } from '~/composables/useAgentFlow'
import type { AgentInputMapping, Model, PromptVersion } from '~/types'

const props = defineProps<{
  id: string
  data: AgentFlowNodeData
  selected?: boolean
}>()

const isActive = computed(() => {
  return props.data?.config?.is_active !== false
})

const agentName = computed(() => props.data?.agent?.name || 'Unknown Agent')
const teamName = computed(() => props.data?.team?.name)
const isSelected = computed(() => props.selected || false)

// Inject lookup arrays from parent flow view
const models = inject<Ref<Model[]>>('agentFlowModels', ref([]))
const promptVersions = inject<Ref<PromptVersion[]>>('agentFlowPromptVersions', ref([]))

const selectedPromptVersion = computed(() => {
  const id = props.data?.config?.prompt_version_id
  if (!id)
    return undefined
  return promptVersions.value.find(v => v.id === id)
})

const promptVariables = computed<string[]>(() => {
  const version = selectedPromptVersion.value
  if (!version?.variables)
    return []
  try {
    const parsed = JSON.parse(version.variables)
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

const inputMappings = computed<AgentInputMapping[]>(() => {
  return props.data?.config?.input_mappings || []
})

function isVariableMapped(variable: string): boolean {
  return inputMappings.value.some(m => m.variable === variable)
}

const promptDisplay = computed(() => {
  const version = selectedPromptVersion.value
  if (!version)
    return 'No prompt'
  const name = version.prompt?.name || 'Unknown'
  return `${name} v${version.version}`
})

const modelDisplay = computed(() => {
  const id = props.data?.config?.model_id
  if (!id)
    return 'No model'
  const model = models.value.find(m => m.id === id)
  return model?.name || 'Model set'
})
</script>

<template>
  <div
    class="agent-node rounded-lg border-2 transition-[border-color,box-shadow,opacity] duration-150 min-w-[180px]"
    :class="{
      'border-primary bg-default shadow-lg': isSelected,
      'border-default bg-default shadow-sm': !isSelected,
      'opacity-60': !isActive,
    }"
  >
    <!-- Target handle (left side - incoming connection) -->
    <VueFlowHandle
      type="target"
      position="left"
      class="!w-3 !h-3 !bg-primary !border-2 !border-[var(--ui-bg)]"
    />

    <!-- Node content -->
    <div class="p-3">
      <!-- Header -->
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0 flex-1">
          <div class="font-medium text-sm text-highlighted truncate">
            {{ agentName }}
          </div>
          <div v-if="teamName" class="text-xs text-muted truncate mt-0.5">
            {{ teamName }}
          </div>
        </div>
        <div
          class="w-2 h-2 rounded-full flex-shrink-0 mt-1.5"
          :class="isActive ? 'bg-success' : 'bg-accented'"
        />
      </div>

      <!-- Config summary -->
      <div class="mt-2 pt-2 border-t border-muted space-y-1.5">
        <div class="flex items-center gap-1 text-xs text-muted">
          <UIcon name="i-lucide-message-square" class="w-3 h-3 flex-shrink-0" />
          <span class="truncate" :title="promptDisplay">
            {{ promptDisplay }}
          </span>
        </div>
        <div class="flex items-center gap-1 text-xs text-muted">
          <UIcon name="i-lucide-brain-circuit" class="w-3 h-3 flex-shrink-0" />
          <span class="truncate" :title="modelDisplay">
            {{ modelDisplay }}
          </span>
        </div>

        <!-- Input variables -->
        <div v-if="promptVariables.length > 0" class="flex flex-wrap gap-1 pt-1">
          <UBadge
            v-for="variable in promptVariables"
            :key="variable"
            size="xs"
            :color="isVariableMapped(variable) ? 'success' : 'warning'"
            variant="subtle"
            class="font-mono"
          >
            {{ variable }}
          </UBadge>
        </div>
      </div>
    </div>

    <!-- Source handle (right side - outgoing connection) -->
    <VueFlowHandle
      type="source"
      position="right"
      class="!w-3 !h-3 !bg-primary !border-2 !border-[var(--ui-bg)]"
    />
  </div>
</template>

<style scoped>
.agent-node {
  /* Prevent text selection during drag */
  user-select: none;
}
</style>
