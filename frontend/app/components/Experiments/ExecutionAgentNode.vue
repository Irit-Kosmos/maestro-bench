<script setup lang="ts">
import type { AgentExecutionSnapshot } from '~/types'

// Read-only node of the execution graph: what the agent ran with, as recorded when the run started
const props = defineProps<{
  data: { snapshot: AgentExecutionSnapshot, step: number }
  selected?: boolean
}>()

const snapshot = computed(() => props.data.snapshot)
const variables = computed(() => parsePromptVariables(snapshot.value.final_variables))
</script>

<template>
  <div
    class="agent-node min-w-[200px] max-w-[240px] rounded-lg border-2 bg-default transition-[border-color,box-shadow] duration-150"
    :class="selected ? 'border-primary shadow-lg' : 'border-default shadow-sm'"
  >
    <VueFlowHandle type="target" position="left" :connectable="false" class="!size-3 !border-2 !border-[var(--ui-bg)] !bg-primary" />

    <div class="p-3">
      <div class="flex items-start gap-2">
        <span class="flex size-5 shrink-0 items-center justify-center rounded-full border border-default text-xs font-medium text-toned tabular-nums">
          <span class="sr-only">Step </span>{{ data.step }}
        </span>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-highlighted" :title="snapshot.agent_name_snapshot">
            {{ snapshot.agent_name_snapshot }}
          </div>
          <div v-if="snapshot.agent_team_name_snapshot && snapshot.agent_team_name_snapshot !== snapshot.agent_name_snapshot" class="mt-0.5 truncate text-xs text-muted">
            {{ snapshot.agent_team_name_snapshot }}
          </div>
        </div>
      </div>

      <div class="mt-2 space-y-1.5 border-t border-muted pt-2">
        <div class="flex items-center gap-1 text-xs text-muted">
          <UIcon name="i-ph-chat-bold" class="size-3 shrink-0" aria-hidden="true" />
          <span class="truncate" :title="`${snapshot.prompt_name_snapshot} v${snapshot.prompt_version_snapshot}`">
            {{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}
          </span>
        </div>
        <ModelsLabel :name="snapshot.model_name_snapshot" :provider="snapshot.model_provider_snapshot" class="text-xs text-muted" />

        <div v-if="variables.length > 0" class="flex flex-wrap gap-1 pt-1">
          <UBadge v-for="variable in variables" :key="variable" size="xs" color="neutral" variant="subtle" class="font-mono">
            {{ variable }}
          </UBadge>
        </div>
      </div>
    </div>

    <VueFlowHandle type="source" position="right" :connectable="false" class="!size-3 !border-2 !border-[var(--ui-bg)] !bg-primary" />
  </div>
</template>

<style scoped>
.agent-node {
  user-select: none;
}
</style>
