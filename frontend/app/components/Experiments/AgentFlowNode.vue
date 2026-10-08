<script setup lang="ts">
import type { AgentFlowNodeData } from '~/composables/useAgentFlow'
import type { AgentInputMapping, Model, PromptVersion } from '~/types'

const props = defineProps<{
  id: string
  data: AgentFlowNodeData
  selected?: boolean
  /** Nothing reads from this node yet: it offers to add what comes next */
  leaf?: boolean
}>()

const isActive = computed(() => props.data?.config?.is_active !== false)
const aggregator = computed(() => props.data?.agent?.kind === 'aggregator')

// Lookups provided by the flow view
const models = inject<Ref<Model[]>>('agentFlowModels', ref([]))
const promptVersions = inject<Ref<PromptVersion[]>>('agentFlowPromptVersions', ref([]))
const order = inject<Ref<Map<number, number>>>('agentFlowOrder', ref(new Map()))

const step = computed(() => order.value.get(props.data.agent.id))
const kicker = computed(() => {
  const label = step.value ? `Step ${step.value}` : 'Step'
  return aggregator.value ? `${label} · Aggregator` : label
})

const selectedPromptVersion = computed(() => {
  const id = props.data?.config?.prompt_version_id
  return id ? promptVersions.value.find(v => v.id === id) : undefined
})

const outputs = computed(() => (props.data?.config?.formulas ?? [])
  .map((f: { name: string }) => f.name)
  .filter(Boolean)
  .join(', '))

const variables = computed<string[]>(() => aggregator.value
  ? formulaVariables(props.data?.config?.formulas)
  : parsePromptVariables(selectedPromptVersion.value?.variables))

const inputMappings = computed<AgentInputMapping[]>(() => props.data?.config?.input_mappings || [])
const unmapped = computed(() => variables.value.filter(v => !inputMappings.value.some(m => m.variable === v)))

const promptDisplay = computed(() => {
  const version = selectedPromptVersion.value
  return version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null
})

const model = computed(() => {
  const id = props.data?.config?.model_id
  return id ? models.value.find(m => m.id === id) : undefined
})
</script>

<template>
  <GraphNodeCard
    :kicker="kicker"
    :icon="aggregator ? 'i-ph-function-bold' : 'i-ph-ghost-bold'"
    :accent="aggregator"
    :title="data.agent.name"
    :subtitle="data.team?.name"
    :selected="selected"
    :muted="!isActive"
  >
    <template v-if="!isActive" #aside>
      <span class="shrink-0 rounded-md border border-default px-1.5 py-0.5 text-[11px] leading-none text-muted">Inactive</span>
    </template>

    <template v-if="aggregator">
      <div class="flex items-center gap-1.5 text-xs" :class="outputs ? 'text-toned' : 'text-warning'">
        <UIcon name="i-ph-function-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="truncate font-mono" :title="outputs">{{ outputs || 'No output' }}</span>
      </div>
    </template>
    <template v-else>
      <div class="flex items-center gap-1.5 text-xs" :class="promptDisplay ? 'text-toned' : 'text-warning'">
        <UIcon name="i-ph-chat-text-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="truncate" :title="promptDisplay ?? undefined">{{ promptDisplay ?? 'No prompt' }}</span>
      </div>
      <div class="flex items-center gap-1.5 text-xs" :class="data.config?.model_id ? 'text-toned' : 'text-warning'">
        <UIProviderIcon v-if="model" :provider="model.provider" class="size-3.5 shrink-0" />
        <UIcon v-else name="i-ph-brain-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
        <span class="truncate" :title="model?.name">{{ data.config?.model_id ? (model?.name || 'Model set') : 'No model' }}</span>
      </div>
    </template>

    <div v-if="variables.length > 0" class="flex flex-wrap gap-1 border-t border-default pt-2">
      <span
        v-for="variable in variables"
        :key="variable"
        class="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 font-mono text-[11px] leading-none"
        :class="unmapped.includes(variable) ? 'border-warning/40 bg-warning/10 text-warning' : 'border-default bg-default text-toned'"
        :title="unmapped.includes(variable) ? `${variable}: not mapped yet` : variable"
      >
        <span class="size-1 shrink-0 rounded-full" :class="unmapped.includes(variable) ? 'bg-warning' : 'bg-success'" aria-hidden="true" />
        {{ variable }}
        <span v-if="unmapped.includes(variable)" class="sr-only">(not mapped)</span>
      </span>
    </div>

    <template v-if="leaf" #footer>
      <ExperimentsAgentFlowAdd :node-id="id" />
    </template>
  </GraphNodeCard>
</template>
