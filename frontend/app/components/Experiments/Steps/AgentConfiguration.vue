<script setup lang="ts">
import type { AgentTeam, Model, PromptVersion } from '~/types'

interface Props {
  selectedTeamId: number | null
  agentConfigurations: Record<number, any>
  agentTeams?: AgentTeam[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
}

interface Emits {
  selectTeam: [teamId: number]
  updateAgentConfig: [agentId: number, field: string, value: any]
  openPromptDetails: [promptVersionId: number]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Get agent management data from props
const agentTeams = computed(() => props.agentTeams || [])
const models = computed(() => props.models || [])
const allPromptVersions = computed(() => props.allPromptVersions || [])

// Get selected team
const selectedTeam = computed(() => {
  return props.selectedTeamId ? agentTeams.value.find(team => team.id === props.selectedTeamId) : null
})

// Create grouped model options for USelectMenu
const modelMenuOptions = computed(() => {
  if (!models.value)
    return []

  const groupedModels: Record<string, any[]> = {}

  // Group models by provider
  models.value
    .filter(model => model.is_active)
    .forEach((model) => {
      if (!groupedModels[model.provider]) {
        groupedModels[model.provider] = []
      }
      groupedModels[model.provider]!.push({
        label: model.name,
        value: model.id,
      })
    })

  // Create the menu structure with separators
  const menuItems: any[] = []
  const providers = Object.keys(groupedModels).sort()

  providers.forEach((provider, index) => {
    // Add provider label
    menuItems.push({
      type: 'label',
      label: provider,
    })

    // Add models for this provider
    groupedModels[provider]!.forEach((model) => {
      menuItems.push(model)
    })

    // Add separator between providers (except for the last one)
    if (index < providers.length - 1) {
      menuItems.push({
        type: 'separator',
      })
    }
  })

  return menuItems
})

// Get selectable model items only (no separators/labels)
const selectableModelItems = computed(() => {
  return modelMenuOptions.value.filter(item => item.value !== undefined)
})

// Create grouped prompt version options for USelectMenu
const promptMenuOptions = computed(() => {
  if (!allPromptVersions.value)
    return []

  const groupedPrompts: Record<string, any[]> = {}

  // Group prompt versions by prompt name
  allPromptVersions.value
    .filter(version => version.is_active)
    .forEach((version) => {
      const promptName = version.prompt?.name || 'Unknown'
      if (!groupedPrompts[promptName]) {
        groupedPrompts[promptName] = []
      }
      groupedPrompts[promptName]!.push({
        label: `v${version.version}${version.is_default ? ' (Default)' : ''}`,
        value: version.id,
      })
    })

  // Create the menu structure with separators
  const menuItems: any[] = []
  const promptNames = Object.keys(groupedPrompts).sort()

  promptNames.forEach((promptName, index) => {
    // Add prompt name label
    menuItems.push({
      type: 'label',
      label: promptName,
    })

    // Add versions for this prompt
    groupedPrompts[promptName]!.forEach((version) => {
      menuItems.push(version)
    })

    // Add separator between prompts (except for the last one)
    if (index < promptNames.length - 1) {
      menuItems.push({
        type: 'separator',
      })
    }
  })

  return menuItems
})

// Get selectable prompt items only (no separators/labels)
const selectablePromptItems = computed(() => {
  return promptMenuOptions.value.filter(item => item.value !== undefined)
})

// Get selected model item for display
function getSelectedModelItem(agentId: number) {
  const modelId = props.agentConfigurations[agentId]?.model_id
  return selectableModelItems.value.find(item => item.value === modelId) || null
}

// Get selected prompt item for display
function getSelectedPromptItem(agentId: number) {
  const promptVersionId = props.agentConfigurations[agentId]?.prompt_version_id
  return selectablePromptItems.value.find(item => item.value === promptVersionId) || null
}

function selectTeam(teamId: number) {
  emit('selectTeam', teamId)
}

function updateAgentConfig(agentId: number, field: string, value: any) {
  emit('updateAgentConfig', agentId, field, value)
}

function openPromptDetails(promptVersionId: number) {
  emit('openPromptDetails', promptVersionId)
}
</script>

<template>
  <div class="space-y-6">
    <!-- Team Selection Grid -->
    <div v-if="agentTeams.length > 0" class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
      <UCard
        v-for="team in agentTeams"
        :key="team.id"
        class="cursor-pointer hover:shadow-md transition-all duration-200"
        :class="{
          'ring-2 ring-primary-500 bg-primary-50': selectedTeamId === team.id,
          'hover:ring-1 hover:ring-neutral-300': selectedTeamId !== team.id,
        }"
        @click="selectTeam(team.id)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="flex items-center justify-between mb-2">
              <h4 class="text-lg font-medium text-neutral-900">
                {{ team.name }}
              </h4>
              <UBadge size="sm" variant="subtle" :color="selectedTeamId === team.id ? 'primary' : 'neutral'">
                {{ team.agents.length }} agent{{ team.agents.length > 1 ? 's' : '' }}
              </UBadge>
            </div>
            <p class="text-sm text-neutral-500 mb-3">
              {{ team.description }}
            </p>
            <div class="flex flex-wrap gap-2">
              <UBadge
                v-for="agent in team.agents"
                :key="agent.id"
                size="sm"
                variant="outline"
                :color="selectedTeamId === team.id ? 'primary' : 'neutral'"
              >
                {{ agent.name }}
              </UBadge>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <!-- No Teams Available -->
    <div v-else class="text-center py-12">
      <UIcon name="i-lucide-users-x" class="h-16 w-16 text-neutral-400 mx-auto mb-4" />
      <h4 class="text-lg font-medium text-neutral-900 mb-2">
        No Agent Teams Available
      </h4>
      <p class="text-neutral-600 mb-6">
        You need to create agent teams before running experiments.
      </p>
      <UButton
        to="/agents"
        icon="i-lucide-plus"
        size="lg"
      >
        Create Agent Teams
      </UButton>
    </div>

    <!-- Agent Configuration Section (appears when team is selected) -->
    <div v-if="selectedTeam" class="border-t border-neutral-200 pt-8">
      <div class="mb-6">
        <h4 class="text-lg font-semibold text-neutral-900 mb-2">
          Configure {{ selectedTeam?.name }} Agents
        </h4>
        <p class="text-neutral-600">
          Select prompt versions and models for each agent, or use their defaults
        </p>
      </div>

      <!-- Agents Configuration Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <UCard
          v-for="agent in selectedTeam?.agents"
          :key="agent.id"
          class="h-fit"
          :class="{
            'ring-2 ring-primary-500 bg-primary-50': agentConfigurations[agent.id]?.is_active === true,
            'hover:ring-1 hover:ring-neutral-300 opacity-70': agentConfigurations[agent.id]?.is_active !== true,
          }"
        >
          <template #header>
            <div class="flex items-center justify-between">
              <div class="mr-4">
                <h5 class="text-base font-medium text-neutral-900">
                  {{ agent.name }}
                </h5>
                <p v-if="agent.description" class="text-sm text-neutral-500 mt-1 pr-4">
                  {{ agent.description }}
                </p>
              </div>
              <USwitch
                :model-value="agentConfigurations[agent.id]?.is_active ?? true"
                @update:model-value="(value: boolean) => updateAgentConfig(agent.id, 'is_active', value)"
              />
            </div>
          </template>

          <!-- Agent Configuration Section -->
          <div>
            <UCollapsible class="flex flex-col">
              <UButton
                class="group justify-between"
                label="Configure Agent"
                variant="ghost"
                icon="i-lucide:settings"
                trailing-icon="i-lucide-chevron-down"
                :ui="{
                  trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
                }"
                :disabled="!agentConfigurations[agent.id]?.is_active"
                block
              />

              <template #content>
                <div class="space-y-4 pt-4">
                  <!-- Prompt Version Selection -->
                  <UFormField label="Prompt Version">
                    <USelectMenu
                      :model-value="getSelectedPromptItem(agent.id)"
                      :items="promptMenuOptions"
                      placeholder="Select prompt version..."
                      class="w-full"
                      @update:model-value="(selectedItem) => updateAgentConfig(agent.id, 'prompt_version_id', selectedItem?.value || null)"
                    />
                    <div v-if="agentConfigurations[agent.id]?.prompt_version_id" class="mt-2 flex justify-end">
                      <UButton
                        variant="ghost"
                        size="xs"
                        icon="i-lucide-eye"
                        @click="openPromptDetails(agentConfigurations[agent.id]?.prompt_version_id!)"
                      >
                        See details
                      </UButton>
                    </div>
                  </UFormField>

                  <!-- Model Selection -->
                  <UFormField label="Model">
                    <USelectMenu
                      :model-value="getSelectedModelItem(agent.id)"
                      :items="modelMenuOptions"
                      placeholder="Select model..."
                      class="w-full"
                      @update:model-value="(selectedItem) => updateAgentConfig(agent.id, 'model_id', selectedItem?.value || null)"
                    />
                  </UFormField>

                  <!-- Advanced Configuration -->
                  <div class="grid grid-cols-2 gap-3">
                    <UFormField label="Temperature">
                      <UInput
                        :model-value="agentConfigurations[agent.id]?.temperature?.toString() || ''"
                        type="number"
                        step="0.1"
                        min="0"
                        max="1"
                        placeholder="0.7"
                        @update:model-value="(value: string) => updateAgentConfig(agent.id, 'temperature', value ? Number.parseFloat(value) : undefined)"
                      />
                    </UFormField>

                    <UFormField label="Max Tokens">
                      <UInput
                        :model-value="agentConfigurations[agent.id]?.max_tokens?.toString() || ''"
                        type="number"
                        min="100"
                        placeholder="10000"
                        @update:model-value="(value: string) => updateAgentConfig(agent.id, 'max_tokens', value ? Number.parseInt(value) : undefined)"
                      />
                    </UFormField>
                  </div>

                  <!-- Reset to Defaults Button -->
                  <div class="flex justify-end pt-2">
                    <UButton
                      variant="ghost"
                      size="xs"
                      icon="i-lucide-rotate-ccw"
                      @click="() => {
                        updateAgentConfig(agent.id, 'reset', {
                          prompt_version_id: agent.default_prompt_version_id || undefined,
                          model_id: agent.default_model_id || undefined,
                          temperature: undefined,
                          max_tokens: undefined,
                          is_active: true,
                        })
                      }"
                    >
                      Reset to Defaults
                    </UButton>
                  </div>
                </div>
              </template>
            </UCollapsible>
          </div>
        </UCard>
      </div>
    </div>
  </div>
</template>
