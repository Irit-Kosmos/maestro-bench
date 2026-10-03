<script setup lang="ts">
import type { Agent, AgentInputMapping, Model, PromptVersion } from '~/types'

// Side panel of the graph view: the same settings as the list, for the selected node
defineProps<{
  agent: Agent | null
  config: Record<string, any> | undefined
  models: Model[]
  allPromptVersions: PromptVersion[]
  datasetHeaders: readonly string[]
  upstreamAgents: Agent[]
}>()

const emit = defineEmits<{
  updateConfig: [field: string, value: any]
  updateInputMapping: [mapping: AgentInputMapping]
  remove: []
  close: []
  reset: []
  openPromptDetails: [promptVersionId: number]
}>()
</script>

<template>
  <div class="flex h-full w-96 shrink-0 flex-col border-l border-default bg-default">
    <header class="flex items-start justify-between gap-2 border-b border-default p-4">
      <div class="min-w-0">
        <h4 class="truncate text-sm font-semibold text-highlighted">
          {{ agent?.name || 'Configure agent' }}
        </h4>
        <p v-if="agent?.description" class="mt-1 text-xs text-muted line-clamp-2">
          {{ agent.description }}
        </p>
      </div>
      <UButton
        variant="ghost"
        size="sm"
        icon="i-ph-x-bold"
        color="neutral"
        aria-label="Close panel"
        @click="emit('close')"
      />
    </header>

    <div v-if="agent" class="flex-1 overflow-y-auto p-4">
      <ExperimentsAggregatorSettings
        v-if="agent.kind === 'aggregator'"
        :config="config"
        :dataset-headers="datasetHeaders"
        :upstream-agents="upstreamAgents"
        @update="(field, value) => emit('updateConfig', field, value)"
        @set-mapping="mapping => emit('updateInputMapping', mapping)"
      />
      <ExperimentsAgentSettings
        v-else
        :config="config"
        :models="models"
        :prompt-versions="allPromptVersions"
        :dataset-headers="datasetHeaders"
        :upstream-agents="upstreamAgents"
        @update="(field, value) => emit('updateConfig', field, value)"
        @set-mapping="mapping => emit('updateInputMapping', mapping)"
        @open-prompt-details="id => emit('openPromptDetails', id)"
      />

      <div class="mt-5 flex flex-col gap-3 border-t border-default pt-4">
        <USwitch
          :model-value="config?.is_active ?? true"
          label="Run this agent"
          size="sm"
          @update:model-value="(value: boolean) => emit('updateConfig', 'is_active', value)"
        />
        <div class="flex items-center justify-between">
          <UButton variant="ghost" color="neutral" size="sm" icon="i-ph-arrow-counter-clockwise-bold" @click="emit('reset')">
            Reset to agent defaults
          </UButton>
          <UButton variant="ghost" color="error" size="sm" icon="i-ph-trash-bold" @click="emit('remove')">
            Remove
          </UButton>
        </div>
      </div>
    </div>
  </div>
</template>
