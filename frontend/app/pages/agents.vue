<script setup lang="ts">
import type { Agent, AgentTeam, Model, PromptVersion } from '~/types'

// Composables
const toast = useToast()
const { createTeam } = useAgentTeams()
const { createAgent, deleteAgent } = useAgents()

// Fetch data directly in the page
const { data: agentTeams, pending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: allPromptVersions, pending: _promptVersionsPending } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: models, pending: _modelsPending } = await useMyLazyFetch<Model[]>('/models')

// Page meta
definePageMeta({
  title: 'Agents',
  subtitle: 'Edit agents in place and organize them into teams',
})

useSeoMeta({
  title: 'Agent Teams',
  description: 'Manage your AI agents and organize them into teams for coordinated experiments.',
})

// Modal states
const showCreateTeamModal = ref(false)
const showCreateAgentModal = ref(false)
const showDeleteAgentModal = ref(false)

// Agent targeted by the delete confirmation
const selectedAgent = ref<Agent | null>(null)

// Rows currently expanded into their editor
const openAgentIds = ref(new Set<number>())

function isOpen(id: number) {
  return openAgentIds.value.has(id)
}

function setOpen(id: number, open: boolean) {
  const next = new Set(openAgentIds.value)
  if (open)
    next.add(id)
  else
    next.delete(id)
  openAgentIds.value = next
}

// Agents grouped under their team (the /agents payload carries the prompt and model details)
const teamGroups = computed(() => (agentTeams.value ?? []).map(team => ({
  ...team,
  agents: (agents.value ?? []).filter(agent => agent.team_id === team.id),
})))

async function refreshAll() {
  await Promise.all([refreshAgents(), refreshTeams()]) // Teams include their agents
}

// Handlers
function handleDeleteAgentClick(agent: Agent) {
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
    await refreshAll()
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
    setOpen(agentId, false)
    selectedAgent.value = null
    await refreshAll()
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

    <BaseEmptyState
      v-if="!agentTeams?.length && !agents?.length"
      icon="i-lucide-bot"
      title="No agents yet"
      message="An agent pairs a prompt version with a model. Agents run together in a team."
      action-label="New team"
      @action="() => { showCreateTeamModal = true }"
    />

    <div v-else class="space-y-8">
      <section
        v-for="team in teamGroups"
        :key="team.id"
        :aria-labelledby="`team-${team.id}`"
      >
        <header class="mb-2 px-1">
          <div class="flex items-baseline gap-2">
            <h2 :id="`team-${team.id}`" class="text-sm font-semibold text-highlighted">
              {{ team.name }}
            </h2>
            <span class="text-xs text-muted tabular-nums">
              {{ team.agents.length }} agent{{ team.agents.length === 1 ? '' : 's' }}
            </span>
          </div>
          <p v-if="team.description" class="mt-0.5 text-sm text-muted text-pretty">
            {{ team.description }}
          </p>
        </header>

        <ul v-if="team.agents.length" class="overflow-hidden rounded-lg border border-default divide-y divide-default">
          <li v-for="agent in team.agents" :key="agent.id">
            <AgentsRow
              :open="isOpen(agent.id)"
              :agent="agent"
              :teams="agentTeams ?? []"
              :prompt-versions="allPromptVersions ?? []"
              :models="models ?? []"
              @update:open="setOpen(agent.id, $event)"
              @saved="refreshAll"
              @delete="handleDeleteAgentClick"
            />
          </li>
        </ul>
        <p v-else class="rounded-lg border border-dashed border-default px-4 py-3 text-sm text-muted">
          No agents in this team yet.
        </p>
      </section>
    </div>

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

    <!-- Delete Agent Modal -->
    <AgentsDeleteAgentModal
      v-model:open="showDeleteAgentModal"
      :agent="selectedAgent"
      @confirm="handleDeleteAgent"
    />
  </BasePageContent>
</template>
