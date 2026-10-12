<script setup lang="ts">
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'

// What one agent ran with, as recorded when the execution started
const props = defineProps<{
  snapshot: AgentExecutionSnapshot
  /** All agents of the execution, to name the source of "previous agent" mappings */
  agents: readonly AgentExecutionSnapshot[]
}>()

const aggregator = computed(() => props.snapshot.kind === 'aggregator')
const formulas = computed(() => parseSnapshotFormulas(props.snapshot))
const variables = computed(() => aggregator.value
  ? formulaVariables(formulas.value)
  : parsePromptVariables(props.snapshot.final_variables))

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
    const name = source?.agent_name_snapshot ?? `agent #${mapping.sourceAgentId}`
    return { label: 'Output of', detail: mapping.sourcePath ? `${name} › ${mapping.sourcePath}` : name, icon: 'i-ph-arrow-elbow-down-right-bold' }
  }
  return { label: aggregator.value ? 'Fixed value' : 'Fixed text', detail: mapping.staticValue ?? '', icon: 'i-ph-cursor-text-bold' }
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
    <dl v-if="!aggregator" class="flex flex-wrap gap-x-8 gap-y-3">
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
          {{ formatCount(snapshot.final_max_tokens) }}
        </dd>
      </div>
    </dl>

    <!-- An aggregator: its formulas, then where their variables came from -->
    <section v-if="aggregator" :aria-labelledby="`formulas-${snapshot.id}`">
      <h4 :id="`formulas-${snapshot.id}`" class="text-sm font-medium text-highlighted">
        Formulas
      </h4>
      <div class="mt-2 divide-y divide-default overflow-hidden rounded-lg border border-default bg-default">
        <ul class="divide-y divide-default">
          <li v-for="f in formulas" :key="f.name" class="px-3 py-2.5 font-mono text-xs">
            <span class="text-highlighted">{{ f.name }}</span>
            <span class="text-dimmed"> = </span>
            <span class="text-toned">{{ f.formula }}</span>
          </li>
        </ul>
        <ul v-if="variables.length > 0" class="divide-y divide-default @2xs:grid @2xs:grid-cols-[minmax(0,max-content)_auto_minmax(0,1fr)] @2xs:gap-x-3">
          <li
            v-for="variable in variables"
            :key="variable"
            class="flex flex-col gap-1 px-3 py-2.5 @2xs:col-span-full @2xs:grid @2xs:grid-cols-subgrid @2xs:items-center"
          >
            <code class="w-fit max-w-40 truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="variable">{{ variable }}</code>
            <UIcon name="i-ph-arrow-right-bold" class="hidden size-3.5 shrink-0 text-dimmed @2xs:block" aria-hidden="true" />
            <span class="flex min-w-0 items-center gap-1.5 text-sm text-toned">
              <UIcon :name="sourceOf(variable).icon" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
              <span class="shrink-0">{{ sourceOf(variable).label }}</span>
              <code v-if="sourceOf(variable).detail" class="min-w-0 truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="sourceOf(variable).detail">{{ sourceOf(variable).detail }}</code>
            </span>
          </li>
        </ul>
      </div>
    </section>

    <!-- The prompt, its inputs and its texts together: one card -->
    <section v-else :aria-labelledby="`prompt-${snapshot.id}`">
      <h4 :id="`prompt-${snapshot.id}`" class="flex items-baseline gap-2 text-sm font-medium text-highlighted">
        <span>Prompt</span>
        <!-- Opens the prompt on the version this run used; older snapshots have no ids to link to -->
        <UIMetaLink v-if="promptLink" :to="promptLink" class="text-sm font-normal">
          {{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}
        </UIMetaLink>
        <span v-else class="min-w-0 truncate font-normal text-muted">{{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}</span>
      </h4>
      <div class="mt-2 divide-y divide-default overflow-hidden rounded-lg border border-default bg-default">
        <ul v-if="variables.length > 0" class="divide-y divide-default @2xs:grid @2xs:grid-cols-[minmax(0,max-content)_auto_minmax(0,1fr)] @2xs:gap-x-3">
          <li
            v-for="variable in variables"
            :key="variable"
            class="flex flex-col gap-1 px-3 py-2.5 @2xs:col-span-full @2xs:grid @2xs:grid-cols-subgrid @2xs:items-center"
          >
            <code class="w-fit max-w-40 truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="variable">{{ variable }}</code>
            <UIcon name="i-ph-arrow-right-bold" class="hidden size-3.5 shrink-0 text-dimmed @2xs:block" aria-hidden="true" />
            <span class="flex min-w-0 items-center gap-1.5 text-sm text-toned">
              <UIcon :name="sourceOf(variable).icon" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
              <span class="shrink-0">{{ sourceOf(variable).label }}</span>
              <code v-if="sourceOf(variable).detail" class="min-w-0 truncate rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-highlighted" :title="sourceOf(variable).detail">{{ sourceOf(variable).detail }}</code>
            </span>
          </li>
        </ul>

        <!-- UCollapsible rather than <details>: the text opens in height with the chevron, like the other disclosures -->
        <!-- The copy button sits over the header row rather than inside the trigger: a button can't nest in a button -->
        <div v-for="prompt in prompts" :key="prompt.label" class="relative">
          <UCollapsible class="group/prompt">
            <button
              type="button"
              class="flex w-full cursor-pointer items-center gap-2 py-2 ps-3 pe-12 text-start text-sm text-highlighted outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
            >
              <UIcon name="i-ph-caret-right-bold" class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) group-data-[state=open]/prompt:rotate-90 motion-reduce:transition-none" aria-hidden="true" />
              {{ prompt.label }}
            </button>
            <template #content>
              <pre class="max-h-80 overflow-auto whitespace-pre-wrap border-t border-default px-3 py-3 font-mono text-xs leading-relaxed text-toned">{{ prompt.content }}</pre>
            </template>
          </UCollapsible>
          <UICopyButton :text="prompt.content!" :label="prompt.label.toLowerCase()" class="absolute end-2 top-1.5" />
        </div>
      </div>
    </section>
  </div>
</template>
