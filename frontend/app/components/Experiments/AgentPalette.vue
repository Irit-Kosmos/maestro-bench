<script setup lang="ts">
import type { Agent, AgentTeam } from '~/types'

interface Props {
  agentTeams: AgentTeam[]
  flowAgentIds: number[]
}

const props = defineProps<Props>()

const emit = defineEmits<{
  addAgent: [agent: Agent]
}>()

// Group agents by team
const teamsWithAgents = computed(() => {
  const result: { team: AgentTeam, agents: Agent[] }[] = []
  props.agentTeams.forEach((team) => {
    if (team.agents && team.agents.length > 0) {
      result.push({ team, agents: [...team.agents] })
    }
  })
  return result
})

function addAgent(agent: Agent) {
  emit('addAgent', agent)
}

function isAgentInFlow(agentId: number): boolean {
  return props.flowAgentIds.includes(agentId)
}
</script>

<template>
  <div class="w-64 flex flex-col border-r border-neutral-200 bg-neutral-50 h-full">
    <!-- Header -->
    <div class="p-3 border-b border-neutral-200">
      <h4 class="font-semibold text-sm text-neutral-900">
        Agents
      </h4>
      <p class="text-xs text-neutral-500 mt-1">
        Click to add to flow
      </p>
    </div>

    <!-- Agent list -->
    <div class="flex-1 overflow-y-auto p-2 space-y-2">
      <div
        v-for="{ team, agents } in teamsWithAgents"
        :key="team.id"
        class="space-y-1"
      >
        <!-- Team header -->
        <div class="flex items-center gap-2 px-2 py-1.5">
          <UIcon name="i-lucide-users" class="w-3.5 h-3.5 text-neutral-400" />
          <span class="text-xs font-medium text-neutral-700 truncate">
            {{ team.name }}
          </span>
          <UBadge size="xs" variant="subtle" class="ml-auto">
            {{ agents.length }}
          </UBadge>
        </div>

        <!-- Agents in team -->
        <div class="space-y-1 pl-2">
          <button
            v-for="agent in agents"
            :key="agent.id"
            class="w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors text-xs"
            :class="{
              'bg-primary-50 text-primary-700 cursor-default': isAgentInFlow(agent.id),
              'hover:bg-white text-neutral-700 cursor-pointer': !isAgentInFlow(agent.id),
            }"
            :disabled="isAgentInFlow(agent.id)"
            @click="addAgent(agent)"
          >
            <UIcon
              name="i-lucide-bot"
              class="w-3.5 h-3.5 flex-shrink-0"
              :class="isAgentInFlow(agent.id) ? 'text-primary-500' : 'text-neutral-400'"
            />
            <span class="truncate">{{ agent.name }}</span>
            <UIcon
              v-if="isAgentInFlow(agent.id)"
              name="i-lucide-check"
              class="w-3.5 h-3.5 text-primary-500 ml-auto flex-shrink-0"
            />
            <UIcon
              v-else
              name="i-lucide-plus"
              class="w-3.5 h-3.5 text-neutral-300 ml-auto flex-shrink-0 opacity-0 group-hover:opacity-100"
            />
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="teamsWithAgents.length === 0" class="text-center py-8 px-4">
        <UIcon name="i-lucide-users-x" class="w-8 h-8 text-neutral-300 mx-auto mb-2" />
        <p class="text-xs text-neutral-500">
          No agents available
        </p>
      </div>
    </div>
  </div>
</template>
