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
import type { Agent, CreateAgentForm, Model, PromptVersion } from '~/types'

// The one field to add an agent to an experiment, in the list and in the graph: typing filters the agents,
// and a name nothing matches can be created from it. An agent already there can be added again: it runs once more.
// The field and its dialog are siblings: the attributes (a width, say) belong to the field
defineOptions({ inheritAttrs: false })

const props = defineProps<{
  agents?: readonly Agent[] | null
  models?: readonly Model[]
  promptVersions?: readonly PromptVersion[]
  /** How many times each agent is already in the experiment */
  addedCounts: ReadonlyMap<number, number>
  /** Reloads the agents, so an agent created here can be added */
  refreshAgents?: () => Promise<void>
}>()

const emit = defineEmits<{
  add: [agent: Agent]
}>()

const { createAgent } = useAgents()
const { canEdit } = useCurrentWorkspace()
const { fail } = useStandardToast()

const NEW_AGENT = 'new:llm'
const NEW_AGGREGATOR = 'new:aggregator'

const search = ref('')
// The menu is only a way to add: it never keeps a selection
const picked = ref<number | string>()

const allAgents = computed(() => props.agents ?? [])
function hintOf(agent: Agent) {
  const count = props.addedCounts.get(agent.id) ?? 0
  const summary = agent.description || defaultSummary(agent)
  if (count === 0)
    return summary
  const added = count === 1 ? 'Already added: add it again' : `Added ${count} times: add it again`
  return summary ? `${added} · ${summary}` : added
}

function defaultSummary(agent: Agent) {
  if (agent.kind === 'aggregator')
    return 'Aggregator'
  const version = props.promptVersions?.find(v => v.id === agent.default_prompt_version_id)
  const model = props.models?.find(m => m.id === agent.default_model_id)
  return [
    version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null,
    model?.name,
  ].filter(Boolean).join(' · ')
}

const menuItems = computed<any[]>(() => {
  const name = search.value.trim()
  const term = name.toLowerCase()

  const entries: any[] = allAgents.value
    .filter(agent => !term || `${agent.name} ${agent.description ?? ''}`.toLowerCase().includes(term))
    .map(agent => ({
      label: agent.name,
      hint: hintOf(agent),
      value: agent.id,
      icon: agent.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold',
    }))

  const taken = allAgents.value.some(agent => agent.name.trim().toLowerCase() === term)
  if (canEdit.value && name && !taken) {
    if (entries.length > 0)
      entries.push({ type: 'separator' as const })
    entries.push(
      { label: `Create agent “${name}”`, value: NEW_AGENT, icon: 'i-ph-ghost-bold', onSelect: () => startCreate('llm', name) },
      { label: `Create aggregator “${name}”`, value: NEW_AGGREGATOR, icon: 'i-ph-function-bold', hint: 'Combines agents with formulas', onSelect: () => startCreate('aggregator', name) },
    )
  }
  return entries
})

function onPick(value: unknown) {
  const agent = typeof value === 'number' ? allAgents.value.find(a => a.id === value) : undefined
  if (agent)
    emit('add', agent)
  nextTick(() => {
    picked.value = undefined
  })
}

// --- Creating an agent on the spot ---

const showCreate = ref(false)
const creating = ref(false)
const createKind = ref<'llm' | 'aggregator'>('llm')
const createName = ref('')

function startCreate(kind: 'llm' | 'aggregator', name: string) {
  createKind.value = kind
  createName.value = name
  showCreate.value = true
}

// An agent created here joins the experiment right away, so the form never loses its place
async function onCreate(data: CreateAgentForm) {
  creating.value = true
  const result = await createAgent(data)
  creating.value = false
  if (!result.success) {
    fail(data.kind === 'aggregator' ? 'Couldn’t create the aggregator' : 'Couldn’t create the agent', result.error)
    return
  }
  showCreate.value = false
  await props.refreshAgents?.()
  emit('add', result.data as Agent)
}
</script>

<template>
  <UInputMenu
    v-model="picked"
    v-model:search-term="search"
    value-key="value"
    :items="menuItems"
    ignore-filter
    open-on-focus
    open-on-click
    icon="i-ph-plus-bold"
    :disabled="!agents"
    placeholder="Add or create an agent"
    class="w-full sm:w-72"
    v-bind="$attrs"
    :ui="{ content: 'w-96 max-w-[calc(100vw-2rem)]' }"
    aria-label="Add or create an agent"
    @update:model-value="onPick"
  >
    <template #item-label="{ item }">
      <span class="flex min-w-0 items-baseline gap-2">
        <span class="shrink-0">{{ item.label }}</span>
        <span v-if="item.hint" class="truncate text-xs font-normal text-muted">{{ item.hint }}</span>
      </span>
    </template>
    <template #empty>
      {{ search.trim() ? 'No agent matches' : 'No agents yet' }}
    </template>
  </UInputMenu>

  <AgentsCreateAgentModal
    v-model:open="showCreate"
    :available-prompt-versions="promptVersions"
    :available-models="models"
    :initial-kind="createKind"
    lock-kind
    :initial-name="createName"
    :loading="creating"
    @submit="onCreate"
  />
</template>
