<script setup lang="ts">
import type { AgentExecutionSnapshot } from '~/types'

// The agents of an execution, in the order they ran, in one card. A sequence is a numbered list of rows
// that open on their settings; a lone agent is the same row, already open and with nothing to fold.
const props = defineProps<{
  agents: readonly AgentExecutionSnapshot[]
}>()

const ordered = computed(() => [...props.agents].sort((a, b) => a.execution_order - b.execution_order))
const sequence = computed(() => ordered.value.length > 1)

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
  <ol class="divide-y divide-default overflow-hidden rounded-lg border border-default">
    <li v-for="(agent, index) in ordered" :key="agent.id">
      <UCollapsible v-if="sequence" :open="openIds.has(agent.id)" class="group/agent" @update:open="(value: boolean) => setOpen(agent.id, value)">
        <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose. -->
        <button
          type="button"
          class="flex h-12 w-full items-center gap-3 px-4 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
        >
          <UIcon
            name="i-ph-caret-right-bold"
            class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/agent:rotate-90"
            aria-hidden="true"
          />
          <span class="flex size-6 shrink-0 items-center justify-center rounded-full border border-default text-xs font-medium text-toned tabular-nums">
            <span class="sr-only">Step </span>{{ index + 1 }}
          </span>
          <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted">{{ agent.agent_name_snapshot }}</span>
          <!-- What identifies the agent at a glance; once open, the body says it in full -->
          <span class="min-w-0 shrink-0 max-w-1/2 text-xs text-muted group-data-[state=open]/agent:hidden">
            <span v-if="agent.kind === 'aggregator'" class="flex items-center gap-1">
              <UIcon name="i-ph-function-bold" class="size-3 shrink-0" aria-hidden="true" />
              <span class="truncate font-mono">{{ parseSnapshotFormulas(agent).map(f => f.name).join(', ') }}</span>
            </span>
            <ModelsLabel v-else :name="agent.model_name_snapshot" :provider="agent.model_provider_snapshot" />
          </span>
        </button>

        <template #content>
          <div class="border-t border-default">
            <ExperimentsAgentSnapshotDetails :snapshot="agent" :agents="ordered" />
          </div>
        </template>
      </UCollapsible>

      <!-- One agent: its name, then the same body, always open. The section's ghost already says "agent", so only an aggregator is marked. -->
      <template v-else>
        <header class="flex items-center gap-2 px-4 pt-3.5">
          <h3 class="truncate text-sm font-semibold text-highlighted">
            {{ agent.agent_name_snapshot }}
          </h3>
          <span v-if="agent.kind === 'aggregator'" class="inline-flex shrink-0 items-center gap-1 text-xs text-muted">
            <UIcon name="i-ph-function-bold" class="size-3" aria-hidden="true" />
            Aggregator
          </span>
        </header>
        <ExperimentsAgentSnapshotDetails :snapshot="agent" :agents="ordered" :class="agent.kind === 'aggregator' ? 'mt-3.5 border-t border-default' : ''" />
      </template>
    </li>
  </ol>
</template>
