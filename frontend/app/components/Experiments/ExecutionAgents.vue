<script setup lang="ts">
import type { AgentExecutionSnapshot } from '~/types'

// The agents of an execution, in the order they ran, shown like the form that created them:
// alone it is one card, in a sequence it is a numbered list of rows that open on their settings.
const props = defineProps<{
  agents: readonly AgentExecutionSnapshot[]
}>()

const ordered = computed(() => [...props.agents].sort((a, b) => a.execution_order - b.execution_order))

// A team named like its only agent adds nothing under the title
function showTeam(agent: AgentExecutionSnapshot) {
  return !!agent.agent_team_name_snapshot && agent.agent_team_name_snapshot !== agent.agent_name_snapshot
}

const openIds = ref(new Set<number>())

function setOpen(id: number, open: boolean) {
  const next = new Set(openIds.value)
  if (open)
    next.add(id)
  else
    next.delete(id)
  openIds.value = next
}
</script>

<template>
  <!-- One agent: a card -->
  <section v-if="ordered.length === 1" class="rounded-lg border border-default">
    <header class="flex items-start gap-3 px-4 py-3">
      <UIcon :name="ordered[0]!.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold'" class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
      <div class="min-w-0">
        <h3 class="truncate text-sm font-semibold text-highlighted">
          {{ ordered[0]!.agent_name_snapshot }}
        </h3>
        <p v-if="showTeam(ordered[0]!)" class="text-xs text-muted">
          {{ ordered[0]!.agent_team_name_snapshot }}
        </p>
      </div>
    </header>
    <div class="border-t border-default bg-elevated/30 px-4 py-4">
      <ExperimentsAgentSnapshotDetails :snapshot="ordered[0]!" :agents="ordered" />
    </div>
  </section>

  <!-- Several agents: numbered rows -->
  <ol v-else class="divide-y divide-default overflow-hidden rounded-lg border border-default">
    <li v-for="(agent, index) in ordered" :key="agent.id">
      <UCollapsible :open="openIds.has(agent.id)" class="group/agent" @update:open="(value: boolean) => setOpen(agent.id, value)">
        <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose. -->
        <button
          type="button"
          class="flex h-14 w-full items-center gap-3 px-4 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
        >
          <UIcon
            name="i-ph-caret-right-bold"
            class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/agent:rotate-90"
            aria-hidden="true"
          />
          <span class="flex size-6 shrink-0 items-center justify-center rounded-full border border-default text-xs font-medium text-toned tabular-nums">
            <span class="sr-only">Step </span>{{ index + 1 }}
          </span>
          <span class="min-w-0 flex-1">
            <span class="flex min-w-0 items-center gap-2">
              <span class="truncate text-sm font-medium text-highlighted">{{ agent.agent_name_snapshot }}</span>
              <span v-if="showTeam(agent)" class="hidden shrink-0 text-xs text-muted sm:inline">{{ agent.agent_team_name_snapshot }}</span>
            </span>
            <span v-if="agent.kind === 'aggregator'" class="mt-0.5 flex min-w-0 items-center gap-1 text-xs text-muted">
              <UIcon name="i-ph-function-bold" class="size-3 shrink-0" aria-hidden="true" />
              <span class="truncate font-mono">{{ parseSnapshotFormulas(agent).map(f => f.name).join(', ') }}</span>
            </span>
            <span v-else class="mt-0.5 flex min-w-0 items-center gap-1 text-xs text-muted">
              <span class="shrink-0">{{ agent.prompt_name_snapshot }} v{{ agent.prompt_version_snapshot }}</span>
              <span aria-hidden="true">·</span>
              <ModelsLabel :name="agent.model_name_snapshot" :provider="agent.model_provider_snapshot" />
            </span>
          </span>
        </button>

        <template #content>
          <div class="border-t border-default bg-elevated/30 px-4 py-4 ps-11">
            <ExperimentsAgentSnapshotDetails :snapshot="agent" :agents="ordered" />
          </div>
        </template>
      </UCollapsible>
    </li>
  </ol>
</template>
