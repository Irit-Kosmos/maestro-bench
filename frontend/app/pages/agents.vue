<script setup lang="ts">
import type { Agent, AgentTeam, Model, PromptVersion } from '~/types'

// Composables
const toast = useToast()
const { createTeam } = useAgentTeams()
const { createAgent, updateAgent, deleteAgent } = useAgents()

// Fetch data directly in the page
const { data: agentTeams, pending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: allPromptVersions, pending: _promptVersionsPending } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: models, pending: _modelsPending } = await useMyLazyFetch<Model[]>('/models')

// Page meta
definePageMeta({
  title: 'Agents',
  subtitle: 'Manage your AI agents and organize them into teams',
})

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
const tabItems = computed(() => [
  {
    label: 'Teams',
    icon: 'i-lucide-users',
    slot: 'teams',
    badge: agentTeams.value?.length ? { label: String(agentTeams.value.length), color: 'neutral' as const, variant: 'soft' as const } : undefined,
  },
  {
    label: 'Agents',
    icon: 'i-lucide-bot',
    slot: 'agents',
    badge: agents.value?.length ? { label: String(agents.value.length), color: 'neutral' as const, variant: 'soft' as const } : undefined,
  },
])
</script>

<template>
  <BasePageContent
    :loading="pending && agentsPending"
  >
    <template #before-content>
      <UButton
        variant="outline"
        color="neutral"
        icon="i-lucide-users-round"
        size="sm"
        @click="() => { showCreateTeamModal = true }"
      >
        New team
      </UButton>
      <UButton
        color="primary"
        icon="i-lucide-plus"
        size="sm"
        @click="() => { showCreateAgentModal = true }"
      >
        New agent
      </UButton>
    </template>

    <!-- Tabs -->
    <UTabs
      :items="tabItems"
      variant="link"
      size="sm"
      :ui="{ root: 'gap-4', list: 'w-full justify-start', trigger: 'grow-0' }"
    >
      <!-- Agent Teams Tab -->
      <template #teams>
        <BaseLoadingState v-if="pending" />

        <BaseEmptyState
          v-else-if="!agentTeams || agentTeams.length === 0"
          icon="i-lucide-users"
          title="No teams yet"
          message="A team groups the agents that run together in an experiment."
          action-label="New team"
          @action="() => { showCreateTeamModal = true }"
        />

        <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <section
            v-for="team in agentTeams"
            :key="team.id"
            class="rounded-lg border border-default p-4"
          >
            <h3 class="text-sm font-semibold text-highlighted">
              {{ team.name }}
            </h3>
            <p v-if="team.description" class="mt-0.5 text-sm text-muted text-pretty">
              {{ team.description }}
            </p>
            <div class="mt-3 flex flex-wrap items-center gap-1.5">
              <span class="text-xs text-muted me-1">{{ team.agents?.length ?? 0 }} agent{{ team.agents?.length === 1 ? '' : 's' }}</span>
              <UBadge
                v-for="agent in team.agents"
                :key="agent.id"
                color="neutral"
                variant="soft"
                size="sm"
                icon="i-lucide-bot"
              >
                {{ agent.name }}
              </UBadge>
            </div>
          </section>
        </div>
      </template>

      <!-- Individual Agents Tab -->
      <template #agents>
        <BaseLoadingState v-if="agentsPending" />

        <BaseEmptyState
          v-else-if="!agents || agents.length === 0"
          icon="i-lucide-bot"
          title="No agents yet"
          message="An agent pairs a prompt version with a model. Add one, then put it in a team."
          action-label="New agent"
          @action="() => { showCreateAgentModal = true }"
        />

        <ul v-else class="rounded-lg border border-default divide-y divide-default">
          <li
            v-for="agent in agents"
            :key="agent.id"
            class="flex items-center gap-4 px-4 py-3"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-baseline gap-2 min-w-0">
                <h3 class="truncate text-sm font-medium text-highlighted">
                  {{ agent.name }}
                </h3>
                <span class="shrink-0 text-xs text-muted">{{ getTeamName(agent.team_id) }}</span>
              </div>
              <p v-if="agent.description" class="mt-0.5 truncate text-sm text-muted" :title="agent.description">
                {{ agent.description }}
              </p>
            </div>

            <div class="hidden md:flex flex-col items-end gap-0.5 shrink-0 text-xs text-toned">
              <span v-if="agent.default_prompt_version" class="inline-flex items-center gap-1">
                <UIcon name="i-lucide-message-square-text" class="size-3 text-muted" aria-hidden="true" />
                {{ agent.default_prompt_version.prompt?.name || 'Unknown' }} v{{ agent.default_prompt_version.version }}
              </span>
              <span v-if="agent.default_model" class="inline-flex items-center gap-1">
                <UIcon name="i-lucide-cpu" class="size-3 text-muted" aria-hidden="true" />
                {{ agent.default_model.name }}
              </span>
            </div>

            <UDropdownMenu
              :items="[
                { label: 'Edit', icon: 'i-lucide-pencil', onSelect: () => handleEditAgent(agent) },
                { label: 'Delete', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => handleDeleteAgentClick(agent) },
              ]"
              :content="{ align: 'end' }"
            >
              <UButton
                icon="i-lucide-ellipsis"
                color="neutral"
                variant="ghost"
                size="sm"
                :aria-label="`Actions for ${agent.name}`"
              />
            </UDropdownMenu>
          </li>
        </ul>
      </template>
    </UTabs>

    <!-- Create Team Modal -->
    <AgentsCreateTeamModal
      v-model:open="showCreateTeamModal"
      :available-agents="agents ?? []"
      @submit="handleCreateTeam"
    />

    <!-- Create Agent Modal -->
    <AgentsCreateAgentModal
      v-model:open="showCreateAgentModal"
      :available-teams="agentTeams ?? []"
      :available-prompt-versions="allPromptVersions ?? []"
      :available-models="models ?? []"
      @submit="handleCreateAgent"
    />

    <!-- Edit Agent Modal -->
    <AgentsEditAgentModal
      v-model:open="showEditAgentModal"
      :agent="selectedAgent"
      :available-teams="agentTeams ?? []"
      :available-prompt-versions="allPromptVersions ?? []"
      :available-models="models ?? []"
      @submit="handleUpdateAgent"
    />

    <!-- Delete Agent Modal -->
    <AgentsDeleteAgentModal
      v-model:open="showDeleteAgentModal"
      :agent="selectedAgent"
      @confirm="handleDeleteAgent"
    />
  </BasePageContent>
</template>
