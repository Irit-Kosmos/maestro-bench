<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { AgentExecutionSnapshot, AgentInputMapping } from '~/types'

// What one agent ran with, as recorded when the execution started
const props = defineProps<{
  snapshot: AgentExecutionSnapshot
  /** All agents of the execution, to name the source of "previous agent" mappings (steps are told apart by key) */
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

// Where a variable comes from. A dataset column is the usual case, so the icon says it and only the column name is written;
// the other sources keep a label ("Output of Content", "Fixed text"…) with the detail that goes next to it
function sourceOf(variable: string) {
  const mapping = mappings.value.find(m => m.variable === variable)
  if (!mapping)
    return { label: 'Matched by name', detail: '', icon: 'i-ph-equals-bold', hint: '' }
  if (mapping.source === 'dataset')
    return { label: '', detail: mapping.sourceColumn ?? '', icon: 'i-ph-table-bold', hint: 'Dataset column' }
  if (mapping.source === 'agent') {
    const wanted = mappingSource(mapping)
    const source = props.agents.find(a => snapshotStep(a) === wanted)
    const name = source?.agent_name_snapshot ?? `agent #${wanted}`
    return { label: 'Output of', detail: mapping.sourcePath ? `${name} › ${mapping.sourcePath}` : name, icon: 'i-ph-arrow-elbow-down-right-bold', hint: '' }
  }
  return { label: aggregator.value ? 'Fixed value' : 'Fixed text', detail: mapping.staticValue ?? '', icon: 'i-ph-cursor-text-bold', hint: '' }
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
  <!-- A body without a frame: the caller draws the card around it (and the agent's name above it) -->
  <div class="@container flex flex-col divide-y divide-default">
    <!-- How it ran: one line of facts -->
    <dl v-if="!aggregator" class="flex flex-wrap items-center gap-x-5 gap-y-1 px-4 py-3 text-sm">
      <div class="flex min-w-0 items-center gap-1.5">
        <dt class="sr-only">
          Model
        </dt>
        <dd class="flex min-w-0 text-highlighted">
          <ModelsLabel :name="snapshot.model_name_snapshot" :provider="snapshot.model_provider_snapshot" />
        </dd>
      </div>
      <div v-if="snapshot.final_temperature !== null && snapshot.final_temperature !== undefined" class="flex items-center gap-1.5">
        <dt class="text-muted">
          Temperature
        </dt>
        <dd class="text-highlighted tabular-nums">
          {{ snapshot.final_temperature }}
        </dd>
      </div>
      <div v-if="snapshot.final_max_tokens" class="flex items-center gap-1.5">
        <dt class="text-muted">
          Max tokens
        </dt>
        <dd class="text-highlighted tabular-nums">
          {{ formatCount(snapshot.final_max_tokens) }}
        </dd>
      </div>
      <div class="flex min-w-0 items-center gap-1.5">
        <dt class="text-muted">
          Prompt
        </dt>
        <dd class="flex min-w-0">
          <!-- Opens the prompt on the version this run used; older snapshots have no ids to link to -->
          <UIMetaLink v-if="promptLink" :to="promptLink">
            {{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}
          </UIMetaLink>
          <span v-else class="truncate text-toned">{{ snapshot.prompt_name_snapshot }} v{{ snapshot.prompt_version_snapshot }}</span>
        </dd>
      </div>
    </dl>

    <!-- An aggregator: its formulas, then where their variables came from -->
    <ul v-if="aggregator" class="divide-y divide-default" aria-label="Formulas">
      <li v-for="f in formulas" :key="f.name" class="px-4 py-2.5 font-mono text-xs">
        <span class="text-highlighted">{{ f.name }}</span>
        <span class="text-dimmed"> = </span>
        <span class="text-toned">{{ f.formula }}</span>
      </li>
    </ul>

    <ul v-if="variables.length > 0" class="divide-y divide-default @2xs:grid @2xs:grid-cols-[minmax(0,max-content)_auto_minmax(0,1fr)] @2xs:gap-x-3" aria-label="Inputs">
      <li
        v-for="variable in variables"
        :key="variable"
        class="flex flex-col gap-1 px-4 py-2.5 @2xs:col-span-full @2xs:grid @2xs:grid-cols-subgrid @2xs:items-center"
      >
        <code class="w-fit max-w-40 truncate font-mono text-xs text-highlighted" :title="variable">{{ variable }}</code>
        <UIcon name="i-ph-arrow-left-bold" class="hidden size-3.5 shrink-0 text-dimmed @2xs:block" aria-hidden="true" />
        <span class="flex min-w-0 items-center gap-1.5 text-sm text-toned" :title="sourceOf(variable).hint || undefined">
          <UIcon :name="sourceOf(variable).icon" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
          <span v-if="sourceOf(variable).hint" class="sr-only">{{ sourceOf(variable).hint }}</span>
          <span v-if="sourceOf(variable).label" class="shrink-0">{{ sourceOf(variable).label }}</span>
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
          class="flex w-full cursor-pointer items-center gap-2 py-2 ps-4 pe-12 text-start text-sm text-highlighted outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
        >
          <UIcon name="i-ph-caret-right-bold" class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) group-data-[state=open]/prompt:rotate-90 motion-reduce:transition-none" aria-hidden="true" />
          {{ prompt.label }}
        </button>
        <template #content>
          <pre class="max-h-80 overflow-auto whitespace-pre-wrap border-t border-default px-4 py-3 font-mono text-xs leading-relaxed text-toned">{{ prompt.content }}</pre>
        </template>
      </UCollapsible>
      <UICopyButton :text="prompt.content!" :label="prompt.label.toLowerCase()" class="absolute end-2 top-1.5" />
    </div>
  </div>
</template>
