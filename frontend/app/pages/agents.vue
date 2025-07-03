<script setup lang="ts">
import type { Agent, AgentTeam } from '~/types'

// Composables
const toast = useToast()
const { createTeam } = useAgentTeams()
const { createAgent, updateAgent, deleteAgent } = useAgents()

// Fetch data directly in the page
const { data: agentTeams, pending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: allPromptVersions, pending: _promptVersionsPending } = await useMyLazyFetch<any[]>('/prompt-versions')
const { data: models, pending: _modelsPending } = await useMyLazyFetch<any[]>('/models')

// Page meta
useSeoMeta({
  title: 'Agent Teams',
  description: 'Manage your AI agents and organize them into teams for coordinated experiments.',
})

// Modal states
const showCreateTeamModal = ref(false)
const showCreateAgentModal = ref(false)
const showEditAgentModal = ref(false)
const showDeleteAgentModal = ref(false)

// Agent details modal
const selectedAgent = ref<any>(null)

// Handlers
function handleConfigureTeam(teamId: number) {
  toast.add({
    title: 'Coming Soon',
    description: `Team configuration coming soon! (Team: ${teamId})`,
    color: 'info',
    icon: 'i-lucide:info',
  })
}

function handleEditAgent(agent: any) {
  selectedAgent.value = agent
  showEditAgentModal.value = true
}

function handleDeleteAgentClick(agent: any) {
  selectedAgent.value = agent
  showDeleteAgentModal.value = true
}

async function handleCreateTeam(data: any) {
  const result = await createTeam(data)
  if (result.success) {
    toast.add({
      title: 'Success',
      description: 'Team created successfully',
      color: 'success',
      icon: 'i-lucide:check',
    })
    await refreshTeams()
  }
  else {
    toast.add({
      title: 'Error',
      description: result.error || 'Failed to create team',
      color: 'error',
      icon: 'i-lucide:x',
    })
  }
}

async function handleCreateAgent(data: any) {
  const result = await createAgent(data)
  if (result.success) {
    toast.add({
      title: 'Success',
      description: 'Agent created successfully',
      color: 'success',
      icon: 'i-lucide:check',
    })
    await refreshAgents()
    await refreshTeams() // Also refresh teams as they include agents
  }
  else {
    toast.add({
      title: 'Error',
      description: result.error || 'Failed to create agent',
      color: 'error',
      icon: 'i-lucide:x',
    })
  }
}

async function handleUpdateAgent(data: any) {
  const result = await updateAgent(data.id, {
    name: data.name,
    description: data.description,
    default_prompt_version_id: data.default_prompt_version_id,
    default_model_id: data.default_model_id,
    team_id: data.team_id,
  })

  if (result.success) {
    toast.add({
      title: 'Success',
      description: 'Agent updated successfully',
      color: 'success',
      icon: 'i-lucide:check',
    })
    showEditAgentModal.value = false
    selectedAgent.value = null
    await refreshAgents()
    await refreshTeams() // Also refresh teams as they include agents
  }
  else {
    toast.add({
      title: 'Error',
      description: result.error || 'Failed to update agent',
      color: 'error',
      icon: 'i-lucide:x',
    })
  }
}

async function handleDeleteAgent(agentId: number) {
  const result = await deleteAgent(agentId)
  if (result.success) {
    toast.add({
      title: 'Success',
      description: 'Agent deleted successfully',
      color: 'success',
      icon: 'i-lucide:check',
    })
    showDeleteAgentModal.value = false
    selectedAgent.value = null
    await refreshAgents()
    await refreshTeams() // Also refresh teams as they include agents
  }
  else {
    toast.add({
      title: 'Error',
      description: result.error || 'Failed to delete agent',
      color: 'error',
      icon: 'i-lucide:x',
    })
  }
}

function getTeamName(teamId: number) {
  const team = agentTeams.value?.find(t => t.id === teamId)
  return team?.name || 'Unknown Team'
}

// Tab items for Nuxt UI UTabs
const tabItems = [
  {
    label: 'Agent Teams',
    icon: 'i-lucide:users',
    slot: 'teams',
  },
  {
    label: 'Individual Agents',
    icon: 'i-lucide:user',
    slot: 'agents',
  },
]
</script>

<template>
  <div class="min-h-screen">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <!-- Page Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h1 class="text-2xl font-bold text-neutral-900">
            Agents Management
          </h1>
          <p class="text-neutral-500 mt-1">
            Manage your AI agents and organize them into teams
          </p>
        </div>
        <div class="flex gap-3">
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide:users-round"
            @click="showCreateTeamModal = true"
          >
            Create Team
          </UButton>
          <UButton
            variant="solid"
            color="primary"
            icon="i-lucide:user-plus"
            size="lg"
            @click="showCreateAgentModal = true"
          >
            Create Agent
          </UButton>
        </div>
      </div>

      <!-- Tabs -->
      <UTabs :items="tabItems" class="w-full">
        <!-- Agent Teams Tab -->
        <template #teams>
          <div class="space-y-6">
            <!-- Loading State -->
            <div v-if="pending" class="flex justify-center items-center py-12">
              <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
            </div>

            <!-- Empty State -->
            <div v-else-if="!agentTeams || agentTeams.length === 0" class="text-center py-12">
              <UIcon name="i-lucide:users" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-neutral-900 mb-2">
                No Agent Teams Found
              </h3>
              <p class="text-neutral-500 mb-4">
                No agent teams have been configured yet. Create your first team to get started.
              </p>
            </div>

            <!-- Agent Teams Grid -->
            <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
              <UCard
                v-for="team in agentTeams"
                :key="team.id"
                class="hover:shadow-md transition-shadow"
              >
                <div class="space-y-4">
                  <div class="flex justify-between w-full items-start">
                    <div class="flex-1 ">
                      <div class="flex justify-between w-full">
                        <h3 class="text-lg font-semibold flex-1 text-neutral-900">
                          {{ team.name }}
                        </h3>

                        <UButton
                          variant="ghost"
                          size="sm"
                          icon="i-lucide:settings"
                          @click="() => handleConfigureTeam(team.id)"
                        />
                      </div>
                      <p class="text-sm text-neutral-600 mt-1">
                        {{ team.description }}
                      </p>
                    </div>
                  </div>

                  <div>
                    <h4 class="text-sm font-medium text-neutral-700 mb-2">
                      Agents:
                    </h4>
                    <div class="flex flex-wrap gap-2">
                      <UBadge
                        v-for="agent in team.agents"
                        :key="agent.id"
                        color="info"
                        variant="outline"
                      >
                        {{ agent.name }}
                      </UBadge>
                    </div>
                  </div>
                </div>
              </UCard>
            </div>
          </div>
        </template>

        <!-- Individual Agents Tab -->
        <template #agents>
          <div class="space-y-6">
            <!-- Loading State -->
            <div v-if="agentsPending" class="flex justify-center items-center py-12">
              <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
            </div>

            <!-- Empty State -->
            <div v-else-if="!agents || agents.length === 0" class="text-center py-12">
              <UIcon name="i-lucide:user" class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
              <h3 class="text-lg font-medium text-neutral-900 mb-2">
                No Agents Found
              </h3>
              <p class="text-neutral-500 mb-4">
                No agents have been created yet. Create your first agent to get started.
              </p>
              <UButton
                variant="solid"
                color="primary"
                icon="i-lucide:user-plus"
                @click="showCreateAgentModal = true"
              >
                Create Your First Agent
              </UButton>
            </div>

            <!-- Agents Grid -->
            <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <UCard
                v-for="agent in agents"
                :key="agent.id"
                class="hover:shadow-md transition-shadow h-fit"
              >
                <div class="space-y-4">
                  <!-- Agent Header -->
                  <div class="flex justify-between items-start">
                    <div class="flex items-center flex-1 space-x-3">
                      <div class="flex flex-1 justify-between">
                        <h3 class="text-lg font-semibold text-neutral-900">
                          {{ agent.name }}
                        </h3>
                        <div class="flex gap-2">
                          <UButton
                            variant="ghost"
                            size="sm"
                            icon="i-lucide:edit"
                            @click="() => handleEditAgent(agent)"
                          />
                          <UButton
                            variant="ghost"
                            size="sm"
                            color="error"
                            icon="i-lucide:trash"
                            @click="() => handleDeleteAgentClick(agent)"
                          />
                        </div>
                      </div>
                    </div>
                  </div>

                  <!-- Agent Details -->
                  <div class="space-y-3">
                    <div v-if="agent.description" class="text-sm text-neutral-600">
                      {{ agent.description }}
                    </div>

                    <div class="grid grid-cols-1 gap-4 text-sm">
                      <div>
                        <span class="font-medium text-neutral-700">Team:</span>
                        <p class="text-neutral-600">
                          {{ getTeamName(agent.team_id) }}
                        </p>
                      </div>
                      <div v-if="agent.default_prompt_version">
                        <span class="font-medium text-neutral-700">Default Prompt:</span>
                        <p class="text-neutral-600 text-xs">
                          {{ agent.default_prompt_version.prompt?.name || 'Unknown' }} v{{ agent.default_prompt_version.version }}
                        </p>
                      </div>
                      <div v-if="agent.default_model">
                        <span class="font-medium text-neutral-700">Default Model:</span>
                        <p class="text-neutral-600 text-xs">
                          {{ agent.default_model.name }} ({{ agent.default_model.provider }})
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </UCard>
            </div>
          </div>
        </template>
      </UTabs>
    </div>

    <!-- Create Team Modal -->
    <AgentsCreateTeamModal
      v-model:open="showCreateTeamModal"
      :available-agents="agents as any"
      @submit="handleCreateTeam"
    />

    <!-- Create Agent Modal -->
    <AgentsCreateAgentModal
      v-model:open="showCreateAgentModal"
      :available-teams="agentTeams as any"
      :available-prompt-versions="allPromptVersions as any"
      :available-models="models as any"
      @submit="handleCreateAgent"
    />

    <!-- Edit Agent Modal -->
    <AgentsEditAgentModal
      v-model:open="showEditAgentModal"
      :agent="selectedAgent"
      :available-teams="agentTeams as any"
      :available-prompt-versions="allPromptVersions as any"
      :available-models="models as any"
      @submit="handleUpdateAgent"
    />

    <!-- Delete Agent Modal -->
    <AgentsDeleteAgentModal
      v-model:open="showDeleteAgentModal"
      :agent="selectedAgent"
      @confirm="handleDeleteAgent"
    />
  </div>
</template>
