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
    return { label: 'Matched by name', detail: '', icon: 'i-ph-equals-bold' }
  if (mapping.source === 'dataset')
    return { label: 'Dataset column', detail: mapping.sourceColumn ?? '', icon: 'i-ph-table-bold' }
  if (mapping.source === 'agent') {
    const source = props.agents.find(a => a.agent_id === mapping.sourceAgentId)
    return { label: 'Output of', detail: source?.agent_name_snapshot ?? `agent #${mapping.sourceAgentId}`, icon: 'i-ph-arrow-elbow-down-right-bold' }
  }
  return { label: 'Fixed text', detail: mapping.staticValue ?? '', icon: 'i-ph-cursor-text-bold' }
}

const promptLink = computed(() => {
  if (!props.snapshot.prompt_id)
    return null
  const version = props.snapshot.prompt_version_id
  return `/prompts/${props.snapshot.prompt_id}${version ? `?v=${version}` : ''}`
})

const prompts = computed(() => [
  { label: 'System prompt', content: props.snapshot.final_system_prompt },
  { label: 'User prompt', content: props.snapshot.final_user_prompt },
].filter(p => !!p.content))
</script>

<template>
  <div class="@container flex flex-col gap-4">
    <dl class="flex flex-wrap gap-x-8 gap-y-3">
      <div class="min-w-0">
        <dt class="text-xs text-muted">
          Model
        </dt>
        <dd class="mt-0.5 text-sm text-highlighted text-pretty">
          <ModelsLabel :name="snapshot.model_name_snapshot" :provider="snapshot.model_provider_snapshot" show-provider class="gap-1.5" />
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

    <!-- The prompt, its inputs and its texts together: one card -->
    <section :aria-labelledby="`prompt-${snapshot.id}`">
      <h4 :id="`prompt-${snapshot.id}`" class="flex items-baseline gap-2 text-sm font-medium text-highlighted">
        <span>Prompt</span>
        <!-- Opens the prompt on the version this run used; older snapshots have no ids to link to -->
        <UIMetaLink v-if="promptLink" :to="promptLink" class="text-sm font-normal">
          {{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}
        </UIMetaLink>
        <span v-else class="min-w-0 truncate font-normal text-muted">{{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}</span>
      </h4>
      <div class="mt-2 divide-y divide-default overflow-hidden rounded-lg border border-default bg-default">
        <ul v-if="variables.length > 0" class="divide-y divide-default">
          <li
            v-for="variable in variables"
            :key="variable"
            class="grid items-center gap-x-3 gap-y-1 px-3 py-2.5 sm:grid-cols-[minmax(6rem,10rem)_auto_minmax(0,1fr)]"
          >
            <code class="w-fit max-w-full truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="variable">{{ variable }}</code>
            <UIcon name="i-ph-arrow-right-bold" class="hidden size-3.5 shrink-0 text-dimmed sm:block" aria-hidden="true" />
            <span class="flex min-w-0 items-center gap-1.5 text-sm text-toned">
              <UIcon :name="sourceOf(variable).icon" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
              <span class="shrink-0">{{ sourceOf(variable).label }}</span>
              <code v-if="sourceOf(variable).detail" class="min-w-0 truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="sourceOf(variable).detail">{{ sourceOf(variable).detail }}</code>
            </span>
          </li>
        </ul>

        <details v-for="prompt in prompts" :key="prompt.label" class="group">
          <summary class="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm text-highlighted outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted [&::-webkit-details-marker]:hidden">
            <UIcon name="i-ph-caret-right-bold" class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) group-open:rotate-90 motion-reduce:transition-none" aria-hidden="true" />
            {{ prompt.label }}
          </summary>
          <pre class="max-h-80 overflow-auto whitespace-pre-wrap border-t border-default px-3 py-3 font-mono text-xs leading-relaxed text-toned">{{ prompt.content }}</pre>
        </details>
      </div>
    </section>
  </div>
</template>
