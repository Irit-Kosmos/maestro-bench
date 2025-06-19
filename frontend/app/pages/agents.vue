<script setup lang="ts">
// Composables
const toast = useToast()
const { agentTeams, pending, createTeam } = useAgentTeams()
const { agents, createAgent } = useAgents()

// Modal states
const showCreateTeamModal = ref(false)
const showCreateAgentModal = ref(false)

// Handlers
function handleConfigureTeam(teamId: number) {
  toast.add({
    title: 'Coming Soon',
    description: `Team configuration coming soon! (Team: ${teamId})`,
    color: 'info',
    icon: 'i-lucide:info',
  })
}

function handleEditPrompts(teamId: number) {
  toast.add({
    title: 'Coming Soon',
    description: `Prompt editor coming soon! (Team: ${teamId})`,
    color: 'info',
    icon: 'i-lucide:info',
  })
}
</script>

<template>
  <div class="min-h-screen">
    <!-- Header Section -->
    <div class="bg-white border-b border-gray-200">
      <!-- Main Content -->
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        <!-- Agent Teams -->
        <div class="flex justify-end items-center gap-3">
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide:users-round"
            @click="showCreateTeamModal = true"
          >
            Create Team
          </UButton>

          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide:user-plus"
            @click="showCreateAgentModal = true"
          >
            Create Agent
          </UButton>
        </div>
        <div>
          <!-- Loading State -->
          <div v-if="pending" class="flex justify-center items-center py-12">
            <UIcon name="i-lucide:loader-2" class="w-8 h-8 animate-spin text-primary-500" />
          </div>

          <!-- Empty State -->
          <div v-else-if="!agentTeams || agentTeams.length === 0" class="text-center py-12">
            <UIcon name="i-lucide:users" class="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 class="text-lg font-medium text-gray-900 mb-2">
              No Agent Teams Found
            </h3>
            <p class="text-gray-500 mb-4">
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
                <div class="flex justify-between items-start">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">
                      {{ team.name }}
                    </h3>
                    <p class="text-sm text-gray-600 mt-1">
                      {{ team.description }}
                    </p>
                  </div>
                </div>

                <div>
                  <h4 class="text-sm font-medium text-gray-700 mb-2">
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

                <div class="flex justify-between items-center pt-3 border-t border-gray-100">
                  <div class="flex space-x-2">
                    <UButton
                      variant="ghost"
                      size="sm"
                      icon="i-lucide:settings"
                      @click="() => handleConfigureTeam(team.id)"
                    >
                      Configure
                    </UButton>
                    <UButton
                      variant="ghost"
                      size="sm"
                      icon="i-lucide:edit"
                      @click="() => handleEditPrompts(team.id)"
                    >
                      Edit Prompts
                    </UButton>
                  </div>
                </div>
              </div>
            </UCard>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Team Modal -->
    <AgentsCreateTeamModal
      v-model:open="showCreateTeamModal"
      :available-agents="agents ? [...agents] : []"
      @submit="createTeam"
    />

    <!-- Create Agent Modal -->
    <AgentsCreateAgentModal
      v-model:open="showCreateAgentModal"
      :available-teams="agentTeams ? [...agentTeams] : []"
      @submit="createAgent"
    />
  </div>
</template>
