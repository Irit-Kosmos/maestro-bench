<script setup lang="ts">
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'

// What one agent ran with, as recorded when the execution started
const props = defineProps<{
  snapshot: AgentExecutionSnapshot
  /** All agents of the execution, to name the source of "previous agent" mappings */
  agents: readonly AgentExecutionSnapshot[]
}>()

const variables = computed(() => parsePromptVariables(props.snapshot.final_variables))

const mappings = computed<AgentInputMapping[]>(() => {
  if (!props.snapshot.final_input_mappings)
    return []
  try {
    const parsed = JSON.parse(props.snapshot.final_input_mappings)
    return Array.isArray(parsed) ? parsed : []
  }
  catch {
    return []
  }
})

// "Dataset column", "Output of Content"… with the detail that goes next to it
function sourceOf(variable: string) {
  const mapping = mappings.value.find(m => m.variable === variable)
  if (!mapping)
    return { label: 'Matched by name', detail: '', icon: 'i-lucide-equal' }
  if (mapping.source === 'dataset')
    return { label: 'Dataset column', detail: mapping.sourceColumn ?? '', icon: 'i-lucide-table-2' }
  if (mapping.source === 'agent') {
    const source = props.agents.find(a => a.agent_id === mapping.sourceAgentId)
    return { label: 'Output of', detail: source?.agent_name_snapshot ?? `agent #${mapping.sourceAgentId}`, icon: 'i-lucide-corner-down-right' }
  }
  return { label: 'Fixed text', detail: mapping.staticValue ?? '', icon: 'i-lucide-text-cursor' }
}

const prompts = computed(() => [
  { label: 'System prompt', content: props.snapshot.final_system_prompt },
  { label: 'User prompt', content: props.snapshot.final_user_prompt },
].filter(p => !!p.content))
</script>

<template>
  <div class="flex flex-col gap-5">
    <dl class="grid gap-x-6 gap-y-3 sm:grid-cols-2 lg:grid-cols-4">
      <div class="min-w-0">
        <dt class="text-xs text-muted">
          Prompt
        </dt>
        <dd class="mt-0.5 text-sm text-highlighted text-pretty">
          {{ snapshot.prompt_name_snapshot }} <span class="text-muted">v{{ snapshot.prompt_version_snapshot }}</span>
        </dd>
      </div>
      <div class="min-w-0">
        <dt class="text-xs text-muted">
          Model
        </dt>
        <dd class="mt-0.5 text-sm text-highlighted text-pretty">
          {{ snapshot.model_name_snapshot }} <span class="text-muted">{{ snapshot.model_provider_snapshot }}</span>
        </dd>
      </div>
      <div v-if="snapshot.final_temperature !== null && snapshot.final_temperature !== undefined">
        <dt class="text-xs text-muted">
          Temperature
        </dt>
        <dd class="mt-0.5 text-sm text-highlighted tabular-nums">
          {{ snapshot.final_temperature }}
        </dd>
      </div>
      <div v-if="snapshot.final_max_tokens">
        <dt class="text-xs text-muted">
          Max tokens
        </dt>
        <dd class="mt-0.5 text-sm text-highlighted tabular-nums">
          {{ snapshot.final_max_tokens.toLocaleString() }}
        </dd>
      </div>
    </dl>

    <section v-if="variables.length > 0" :aria-labelledby="`vars-${snapshot.id}`">
      <h4 :id="`vars-${snapshot.id}`" class="text-sm font-medium text-highlighted">
        Prompt variables
      </h4>
      <ul class="mt-2 divide-y divide-default rounded-lg border border-default bg-default">
        <li
          v-for="variable in variables"
          :key="variable"
          class="grid items-baseline gap-x-3 gap-y-0.5 px-3 py-2 sm:grid-cols-[minmax(6rem,10rem)_minmax(0,1fr)]"
        >
          <code class="truncate font-mono text-xs text-highlighted" :title="variable">{{ variable }}</code>
          <span class="flex min-w-0 items-baseline gap-1.5 text-sm text-toned">
            <UIcon :name="sourceOf(variable).icon" class="size-3.5 shrink-0 translate-y-0.5 text-muted" aria-hidden="true" />
            <span class="shrink-0">{{ sourceOf(variable).label }}</span>
            <code v-if="sourceOf(variable).detail" class="min-w-0 truncate font-mono text-xs text-highlighted" :title="sourceOf(variable).detail">{{ sourceOf(variable).detail }}</code>
          </span>
        </li>
      </ul>
    </section>

    <div v-if="prompts.length > 0" class="flex flex-col gap-2">
      <details v-for="prompt in prompts" :key="prompt.label" class="group rounded-lg border border-default bg-default">
        <summary class="flex cursor-pointer list-none items-center gap-2 rounded-lg px-3 py-2 text-sm text-highlighted outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary [&::-webkit-details-marker]:hidden">
          <UIcon name="i-lucide-chevron-right" class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) group-open:rotate-90 motion-reduce:transition-none" aria-hidden="true" />
          {{ prompt.label }}
        </summary>
        <pre class="max-h-80 overflow-auto whitespace-pre-wrap border-t border-default px-3 py-3 font-mono text-xs leading-relaxed text-toned">{{ prompt.content }}</pre>
      </details>
    </div>
  </div>
</template>
