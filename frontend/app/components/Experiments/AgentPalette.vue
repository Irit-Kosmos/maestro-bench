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
  <div class="w-64 flex flex-col border-r border-default bg-muted h-full">
    <!-- Header -->
    <div class="p-3 border-b border-default">
      <h4 class="font-semibold text-sm text-highlighted">
        Agents
      </h4>
      <p class="text-xs text-muted mt-1">
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
          <UIcon name="i-ph-users-bold" class="size-3.5 text-dimmed" />
          <span class="text-xs font-medium text-default truncate">
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
            class="group w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left transition-colors text-xs"
            :class="{
              'bg-primary/10 text-primary cursor-default': isAgentInFlow(agent.id),
              'hover:bg-default text-default cursor-pointer': !isAgentInFlow(agent.id),
            }"
            :disabled="isAgentInFlow(agent.id)"
            @click="addAgent(agent)"
          >
            <UIcon
              :name="agent.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold'"
              class="size-3.5 shrink-0"
              :class="isAgentInFlow(agent.id) ? 'text-primary' : 'text-dimmed'"
            />
            <span class="truncate">{{ agent.name }}</span>
            <UIcon
              v-if="isAgentInFlow(agent.id)"
              name="i-ph-check-bold"
              class="size-3.5 text-primary ml-auto shrink-0"
            />
            <UIcon
              v-else
              name="i-ph-plus-bold"
              class="size-3.5 text-dimmed ml-auto shrink-0 opacity-0 group-hover:opacity-100"
            />
          </button>
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="teamsWithAgents.length === 0" class="text-center py-8 px-4">
        <UIcon name="i-ph-user-minus-bold" class="size-8 text-dimmed mx-auto mb-2" />
        <p class="text-xs text-muted">
          No agents available
        </p>
      </div>
    </div>
  </div>
</template>
