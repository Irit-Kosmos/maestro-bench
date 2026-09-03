<script setup lang="ts">
import type { Agent, AgentInputMapping, Model, PromptVersion } from '~/types'

interface Props {
  agent: Agent | null
  config: Record<string, any> | undefined
  models: Model[]
  allPromptVersions: PromptVersion[]
  datasetHeaders: readonly string[]
  upstreamAgents: Agent[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  updateConfig: [field: string, value: any]
  updateInputMapping: [mapping: AgentInputMapping]
  removeInputMapping: [variable: string]
  remove: []
  reset: []
  openPromptDetails: [promptVersionId: number]
}>()

// Create grouped model options for USelectMenu
const modelMenuOptions = computed(() => {
  if (!props.models || props.models.length === 0)
    return []

  const groupedModels: Record<string, any[]> = {}

  props.models
    .filter(model => model.is_active)
    .forEach((model) => {
      if (!groupedModels[model.provider])
        groupedModels[model.provider] = []
      groupedModels[model.provider]!.push({
        label: model.name,
        value: model.id,
      })
    })

  const menuItems: any[] = []
  const providers = Object.keys(groupedModels).sort()

  providers.forEach((provider, index) => {
    menuItems.push({
      type: 'label',
      label: provider,
    })

    groupedModels[provider]!.forEach((model) => {
      menuItems.push(model)
    })

    if (index < providers.length - 1)
      menuItems.push({ type: 'separator' })
  })

  return menuItems
})

// Create grouped prompt version options for USelectMenu
const promptMenuOptions = computed(() => {
  if (!props.allPromptVersions || props.allPromptVersions.length === 0)
    return []

  const groupedPrompts: Record<string, any[]> = {}

  props.allPromptVersions
    .filter(version => version.is_active)
    .forEach((version) => {
      const promptName = version.prompt?.name || 'Unknown'
      if (!groupedPrompts[promptName])
        groupedPrompts[promptName] = []
      groupedPrompts[promptName]!.push({
        label: `${version.version}${version.is_default ? ' (Default)' : ''}`,
        value: version.id,
      })
    })

  const menuItems: any[] = []
  const promptNames = Object.keys(groupedPrompts).sort()

  promptNames.forEach((promptName, index) => {
    menuItems.push({
      type: 'label',
      label: promptName,
    })

    groupedPrompts[promptName]!.forEach((version) => {
      menuItems.push(version)
    })

    if (index < promptNames.length - 1)
      menuItems.push({ type: 'separator' })
  })

  return menuItems
})

function updateField(field: string, value: any) {
  emit('updateConfig', field, value)
}

// --- Input Variables / Mappings ---

const sourceOptions = [
  { label: 'Dataset column', value: 'dataset' },
  { label: 'Previous agent output', value: 'agent' },
  { label: 'Static value', value: 'static' },
]

const outputOptions = [
  { label: 'Full output', value: 'output' },
]

const datasetHeaderOptions = computed(() => {
  return props.datasetHeaders.map(header => ({ label: header, value: header }))
})

const upstreamAgentOptions = computed(() => {
  return props.upstreamAgents.map(agent => ({ label: agent.name, value: agent.id }))
})

// Parse variables from the selected prompt version
const promptVariables = computed<string[]>(() => {
  const promptVersionId = props.config?.prompt_version_id
  if (!promptVersionId)
    return []
  const version = props.allPromptVersions.find(v => v.id === promptVersionId)
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
  return props.config?.input_mappings || []
})

function getVariableMapping(variable: string): AgentInputMapping | undefined {
  return inputMappings.value.find(m => m.variable === variable)
}

const hasDatasetHeaders = computed(() => props.datasetHeaders.length > 0)

// Reactive list of variables enriched with their current mapping.
// Using this in the v-for ensures every conditional field re-renders when a mapping changes.
const variablesWithMappings = computed(() => {
  return promptVariables.value.map((variable) => {
    const mapping = getVariableMapping(variable)
    return {
      variable,
      mapping,
      source: mapping?.source,
      isMapped: mapping !== undefined,
    }
  })
})

function updateSource(variable: string, source: string) {
  if (!source) {
    emit('removeInputMapping', variable)
    return
  }

  const existing = getVariableMapping(variable)
  const base: AgentInputMapping = {
    variable,
    source: source as 'dataset' | 'agent' | 'static',
  }

  if (source === 'dataset') {
    base.sourceColumn = existing?.sourceColumn || props.datasetHeaders[0] || undefined
  }
  else if (source === 'agent') {
    base.sourceAgentId = existing?.sourceAgentId || props.upstreamAgents[0]?.id
    base.sourceOutput = existing?.sourceOutput || 'output'
  }
  else if (source === 'static') {
    base.staticValue = existing?.staticValue || ''
  }

  emit('updateInputMapping', base)
}

function updateMappingField(variable: string, field: keyof AgentInputMapping, value: any) {
  const existing = getVariableMapping(variable)
  if (!existing)
    return
  emit('updateInputMapping', {
    ...existing,
    [field]: value,
  })
}
</script>

<template>
  <div class="w-80 flex flex-col h-full bg-white border-l border-neutral-200">
    <!-- Header -->
    <div class="p-4 border-b border-neutral-200 flex items-center justify-between">
      <div>
        <h4 class="font-semibold text-sm text-neutral-900">
          {{ agent?.name || 'Configure Agent' }}
        </h4>
        <p v-if="agent?.description" class="text-xs text-neutral-500 mt-1 line-clamp-2">
          {{ agent.description }}
        </p>
      </div>
      <UButton
        variant="ghost"
        size="xs"
        icon="i-lucide-x"
        color="neutral"
        @click="emit('remove')"
      />
    </div>

    <!-- Config Form -->
    <div v-if="agent" class="flex-1 overflow-y-auto p-4 space-y-4">
      <!-- Active toggle -->
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium text-neutral-900">Active</span>
        <USwitch
          :model-value="config?.is_active ?? true"
          @update:model-value="(value: boolean) => updateField('is_active', value)"
        />
      </div>

      <USeparator />

      <!-- Prompt Version Selection -->
      <UFormField label="Prompt Version">
        <USelectMenu
          :model-value="config?.prompt_version_id"
          value-key="value"
          :items="promptMenuOptions"
          placeholder="Select prompt version..."
          class="w-full"
          @update:model-value="(value) => updateField('prompt_version_id', value || null)"
        />
        <div v-if="config?.prompt_version_id" class="mt-2 flex justify-end">
          <UButton
            variant="ghost"
            size="xs"
            icon="i-lucide-eye"
            @click="$emit('openPromptDetails', config.prompt_version_id)"
          >
            See details
          </UButton>
        </div>
      </UFormField>

      <!-- Model Selection -->
      <UFormField label="Model">
        <USelectMenu
          :model-value="config?.model_id"
          value-key="value"
          :items="modelMenuOptions"
          placeholder="Select model..."
          class="w-full"
          @update:model-value="(value) => updateField('model_id', value || null)"
        />
      </UFormField>

      <!-- Advanced Configuration -->
      <div class="grid grid-cols-2 gap-3">
        <UFormField label="Temperature">
          <UInput
            :model-value="config?.temperature?.toString() || ''"
            type="number"
            step="0.1"
            min="0"
            max="1"
            placeholder="0.7"
            @update:model-value="(value: string) => updateField('temperature', value !== '' ? Number.parseFloat(value) : undefined)"
          />
        </UFormField>

        <UFormField label="Max Tokens">
          <UInput
            :model-value="config?.max_tokens?.toString() || ''"
            type="number"
            min="100"
            placeholder="10000"
            @update:model-value="(value: string) => updateField('max_tokens', value !== '' ? Number.parseInt(value) : undefined)"
          />
        </UFormField>
      </div>

      <USeparator />

      <!-- Input Variables / Mappings -->
      <div v-if="promptVariables.length > 0" class="space-y-3">
        <div class="flex items-center justify-between">
          <h5 class="text-sm font-medium text-neutral-900">
            Input Variables
          </h5>
          <UBadge size="xs" variant="subtle">
            {{ promptVariables.length }}
          </UBadge>
        </div>

        <div
          v-for="{ variable, source, isMapped, mapping } in variablesWithMappings"
          :key="variable"
          class="border border-neutral-200 rounded-md p-3 space-y-2"
        >
          <div class="flex items-center justify-between">
            <code class="text-xs font-medium text-primary-700 bg-primary-50 px-2 py-0.5 rounded">
              {{ variable }}
            </code>
            <UBadge
              size="xs"
              :color="isMapped ? 'success' : 'warning'"
              variant="subtle"
            >
              {{ isMapped ? 'Mapped' : 'Unmapped' }}
            </UBadge>
          </div>

          <UFormField label="Source" class="mb-0">
            <USelectMenu
              :model-value="source"
              value-key="value"
              :items="sourceOptions"
              placeholder="Select source..."
              class="w-full"
              @update:model-value="(newSource) => updateSource(variable, newSource as string)"
            />
          </UFormField>

          <!-- Dataset column selector -->
          <div v-if="source === 'dataset'" class="space-y-2">
            <UFormField v-if="hasDatasetHeaders" label="Column">
              <USelectMenu
                :model-value="mapping?.sourceColumn"
                value-key="value"
                :items="datasetHeaderOptions"
                placeholder="Select column..."
                class="w-full"
                @update:model-value="(value) => updateMappingField(variable, 'sourceColumn', value as string)"
              />
            </UFormField>
            <UAlert
              v-else
              color="warning"
              variant="subtle"
              icon="i-lucide-triangle-alert"
              title="No dataset columns"
              description="Select a dataset first so its columns can be mapped to this variable."
            />
          </div>

          <!-- Previous agent output selectors -->
          <div v-if="source === 'agent'" class="space-y-2">
            <UFormField label="Agent">
              <USelectMenu
                :model-value="mapping?.sourceAgentId"
                value-key="value"
                :items="upstreamAgentOptions"
                placeholder="Select agent..."
                class="w-full"
                @update:model-value="(value) => updateMappingField(variable, 'sourceAgentId', value as number)"
              />
            </UFormField>
            <UFormField label="Output">
              <USelectMenu
                :model-value="mapping?.sourceOutput || 'output'"
                value-key="value"
                :items="outputOptions"
                class="w-full"
                @update:model-value="(value) => updateMappingField(variable, 'sourceOutput', value as string)"
              />
            </UFormField>
          </div>

          <!-- Static value input -->
          <UFormField v-if="source === 'static'" label="Value">
            <UInput
              :model-value="mapping?.staticValue"
              placeholder="Enter static value..."
              class="w-full"
              @update:model-value="(value) => updateMappingField(variable, 'staticValue', value)"
            />
          </UFormField>
        </div>
      </div>

      <USeparator />

      <!-- Actions -->
      <div class="flex justify-between items-center">
        <UButton
          variant="ghost"
          size="xs"
          icon="i-lucide-rotate-ccw"
          @click="emit('reset')"
        >
          Reset to Defaults
        </UButton>

        <UButton
          variant="soft"
          size="xs"
          color="error"
          icon="i-lucide-trash-2"
          @click="emit('remove')"
        >
          Remove from Flow
        </UButton>
      </div>
    </div>
  </div>
</template>
