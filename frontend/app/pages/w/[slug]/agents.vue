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
import type { Agent, AgentKind, Model, PromptVersion, Tag } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import type { SortSpec } from '~/utils/sorts'
import { h, resolveComponent } from 'vue'
import { useGroupBy } from '~/composables/useGroupBy'
import { useSortBy } from '~/composables/useSortBy'
import { byOrder } from '~/utils/filters'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'
import { dateSort, nameSort, textSort } from '~/utils/sortSpecs'

// Composables
const { showCreateSuccess, showCreateError, showDeleteSuccess, showDeleteError, ok } = useStandardToast()
const { createAgent, deleteAgent } = useAgents()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

// Fetch data directly in the page
const { data: agents, pending: agentsPending, error: agentsError, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: allPromptVersions, pending: _promptVersionsPending } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: models, pending: _modelsPending } = await useMyLazyFetch<Model[]>('/models')

// Page meta
definePageMeta({
  title: 'Agents',
})

useSeoMeta({
  title: 'Agents',
  description: 'Manage your AI agents and aggregators and tag them to find them again.',
})

// Modal states
const showCreateAgentModal = ref(false)
const showDeleteAgentModal = ref(false)
const creatingAgent = ref(false)
const deletingAgent = ref(false)

// Agent targeted by the delete confirmation
const selectedAgent = ref<Agent | null>(null)

// An agent as a row: the API returns ids, so the names the table shows and searches are resolved here
interface AgentRow extends Agent {
  kind: AgentKind
  tags: Tag[]
  prompt_label: string | null
  model: Model | null
}

const rows = computed<AgentRow[]>(() => {
  const versions = new Map((allPromptVersions.value ?? []).map(version => [version.id, version]))
  const modelsById = new Map((models.value ?? []).map(model => [model.id, model]))
  return (agents.value ?? [])
    .map((agent) => {
      const version = agent.default_prompt_version_id == null ? undefined : versions.get(agent.default_prompt_version_id)
      return {
        ...agent,
        kind: agent.kind ?? 'llm',
        tags: agent.tags ?? [],
        prompt_label: version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null,
        model: agent.default_model_id == null ? null : modelsById.get(agent.default_model_id) ?? null,
      }
    })
    .sort((a, b) => a.name.localeCompare(b.name))
})

// Table
const UIcon = resolveComponent('UIcon')

const columns = [
  {
    key: 'name',
    width: 240,
    label: 'Agent',
    // The description is not shown, but the search still reads it
    formatter: (_: unknown, row: AgentRow) => `${row.name} ${row.description ?? ''}`,
    render: (row: AgentRow) => h('span', { class: 'flex min-h-9 min-w-0 items-center gap-3' }, [
      // The tile is what tells an aggregator from a model call at a glance
      h('span', {
        'class': ['flex size-7 shrink-0 items-center justify-center rounded-md', row.kind === 'aggregator' ? 'bg-info/10 text-info' : 'bg-elevated text-muted'],
        'aria-hidden': 'true',
      }, [h(UIcon, { name: row.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold', class: 'size-4' })]),
      h('span', { class: 'truncate', title: row.description ?? undefined }, row.name),
    ]),
  },
  { key: 'kind', width: 136, label: 'Type', formatter: (_: unknown, row: AgentRow) => row.kind === 'aggregator' ? 'Aggregator' : 'LLM' },
  {
    key: 'tags',
    width: 240,
    label: 'Tags',
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, row: AgentRow) => row.tags.map(tag => tag.name).join(' '),
  },
  { key: 'default_prompt_version_id', width: 170, label: 'Prompt', formatter: (_: unknown, row: AgentRow) => row.prompt_label ?? '' },
  { key: 'default_model_id', width: 180, label: 'Model', formatter: (_: unknown, row: AgentRow) => row.model?.name ?? '' },
  { key: 'created_at', width: 112, label: 'Created' },
]

const KINDS = {
  llm: { label: 'LLM', icon: 'i-ph-ghost-bold' },
  aggregator: { label: 'Aggregator', icon: 'i-ph-function-bold' },
} as const

const filters: FilterSpec<AgentRow>[] = [
  {
    key: 'kind',
    label: 'Type',
    icon: 'i-ph-shapes-bold',
    multiple: false,
    value: agent => agent.kind,
    present: value => KINDS[value as AgentKind] ?? { label: String(value) },
    compare: byOrder(Object.keys(KINDS)),
  },
  {
    key: 'model',
    label: 'Model',
    icon: 'i-ph-cpu-bold',
    plural: 'models',
    searchPlaceholder: 'Search a model…',
    value: agent => agent.model?.name,
  },
  tagsFilter<AgentRow>(agent => agent.tags),
  dateFilter<AgentRow>(agent => agent.created_at),
]

// Sections the list can be cut into; the choice is remembered per browser
const groups: GroupSpec<AgentRow>[] = [
  {
    key: 'kind',
    label: 'Type',
    icon: 'i-ph-shapes-bold',
    value: agent => agent.kind,
    present: value => KINDS[value as AgentKind] ?? { label: String(value) },
    compare: byOrder(Object.keys(KINDS)),
  },
  {
    key: 'model',
    label: 'Model',
    icon: 'i-ph-cpu-bold',
    value: agent => agent.model?.name,
    emptyLabel: 'No model',
  },
  {
    key: 'prompt',
    label: 'Prompt',
    icon: 'i-ph-chat-text-bold',
    value: agent => agent.prompt_label,
    emptyLabel: 'No prompt',
  },
]
const groupBy = useGroupBy('maestro:agents-group-by', null)

// In the order of the columns. The list is by name until one is picked; inside a section the agents are sorted among themselves
const sortBy = useSortBy('maestro:agents-sort-by')
const sorts: SortSpec<AgentRow>[] = [
  nameSort(agent => agent.name, 'Agent'),
  textSort('kind', 'Type', 'i-ph-shapes-bold', agent => KINDS[agent.kind].label),
  textSort('prompt', 'Prompt', 'i-ph-chat-text-bold', agent => agent.prompt_label),
  textSort('model', 'Model', 'i-ph-cpu-bold', agent => agent.model?.name),
  dateSort(agent => agent.created_at),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})

const actions = [
  {
    label: 'Edit',
    icon: 'i-ph-pencil-simple-bold',
    requires: 'editor' as const,
    handler: (agent: AgentRow) => openPanel(agent.id),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
    handler: (agent: AgentRow) => handleDeleteAgentClick(agent),
  },
]

// What the table shows, in order: the panel moves through it
const table = useTemplateRef<{ rows: AgentRow[] }>('table')
const shown = computed(() => table.value?.rows ?? [])

const openId = ref<number | null>(null)
const panelOpen = ref(false)
const openIndex = computed(() => shown.value.findIndex(agent => agent.id === openId.value))
const openAgent = computed(() => (agents.value ?? []).find(agent => agent.id === openId.value) ?? null)

function openPanel(id: number) {
  openId.value = id
  panelOpen.value = true
}

function moveInPanel(delta: number) {
  const next = shown.value[openIndex.value + delta]
  if (next)
    openId.value = next.id
}

// A link such as /agents?agent=<id> opens that agent's panel, once the list is there
const agentFromLink = Number(useRoute().query.agent) || undefined
const stopLinkOpen = watch(agents, (list) => {
  if (!agentFromLink || !list?.some(agent => agent.id === agentFromLink))
    return
  openPanel(agentFromLink)
  nextTick(() => stopLinkOpen())
}, { immediate: true })

async function refreshAll() {
  await refreshAgents()
}

useCreateFromQuery(() => {
  showCreateAgentModal.value = true
})

// Handlers
function handleDeleteAgentClick(agent: Agent) {
  selectedAgent.value = agent
  showDeleteAgentModal.value = true
}

async function handleCreateAgent(data: any) {
  creatingAgent.value = true
  const result = await createAgent(data)
  creatingAgent.value = false
  if (result.success) {
    showCreateAgentModal.value = false
    if (data.kind === 'aggregator')
      ok('Aggregator created')
    else
      showCreateSuccess('Agent')
    await refreshAll()
  }
  else {
    showCreateError(data.kind === 'aggregator' ? 'Aggregator' : 'Agent', result.error)
  }
}

async function handleDeleteAgent() {
  const agentId = selectedAgent.value?.id
  if (agentId === undefined)
    return
  deletingAgent.value = true
  const result = await deleteAgent(agentId)
  deletingAgent.value = false
  if (result.success) {
    showDeleteSuccess('Agent')
    showDeleteAgentModal.value = false
    if (openId.value === agentId)
      panelOpen.value = false
    await refreshAll()
  }
  else {
    showDeleteError('Agent', result.error)
  }
}
</script>

<template>
  <!-- Loading only until the first data arrives: a refresh (after a save) must not unmount the panel -->
  <BasePageContent
    :loading="agentsPending && !agents"
    :error="!agents && !!agentsError"
    :error-kind="fetchErrorKind(agentsError)"
    @retry="refreshAgents"
  >
    <template #before-content>
      <UIGuardedButton
        color="neutral"
        variant="soft"
        icon="i-ph-plus-bold"
        size="sm"
        @click="() => { showCreateAgentModal = true }"
      >
        New agent
      </UIGuardedButton>
    </template>

    <BaseDataTable
      v-if="rows.length"
      ref="table"
      v-model:filter-state="filterState"
      v-model:group-by="groupBy"
      v-model:sort-by="sortBy"
      :data="rows"
      :columns="columns"
      :filters="filters"
      :groups="groups"
      :sorts="sorts"
      :actions="actions"
      :loading="agentsPending"
      :row-open="(agent: AgentRow) => openPanel(agent.id)"
      :active-key="panelOpen ? openId : null"
      item-name="agent"
      searchable
      :selectable="canEdit"
      @refresh="refreshAll"
    >
      <template #selection-actions="{ rows: selectedRows }">
        <TagsBulkMenu kind="agent" :rows="selectedRows" @changed="refreshAgents" />
      </template>

      <template #kind-cell="{ row }">
        <AgentsKindBadge :kind="row.original.kind" />
      </template>

      <!-- An aggregator has neither: its inputs and formulas are set in each experiment -->
      <template #default_prompt_version_id-cell="{ row }">
        <span v-if="row.original.prompt_label" class="block truncate text-sm text-toned" :title="row.original.prompt_label">{{ row.original.prompt_label }}</span>
        <span v-else class="text-dimmed">—</span>
      </template>

      <template #default_model_id-cell="{ row }">
        <ModelsLabel v-if="row.original.model" :name="row.original.model.name" :provider="row.original.model.provider" />
        <span v-else class="text-dimmed">—</span>
      </template>

      <template #tags-cell="{ row }">
        <TagsList
          :id="row.original.id"
          :tags="row.original.tags"
          kind="agent"
          :max="2"
          selectable
          @changed="refreshAgents"
          @select="tag => { filterState = filterByTag(filterState, tag.name) }"
        />
      </template>

      <template #created_at-cell="{ row }">
        <span class="text-sm text-muted" :title="formatDate(row.original.created_at)">
          {{ formatRelativeDate(row.original.created_at) }}
        </span>
      </template>
    </BaseDataTable>

    <BaseEmptyState
      v-else-if="!agentsPending"
      icon="i-ph-ghost-bold"
      title="No agents yet"
      message="An agent pairs a prompt version with a model; an aggregator combines the outputs of other agents."
      action-label="New agent"
      action-requires="editor"
      @action="() => { showCreateAgentModal = true }"
    />

    <AgentsPanel
      v-model:open="panelOpen"
      :agent="openAgent"
      :index="openIndex"
      :total="shown.length"
      :prompt-versions="allPromptVersions ?? []"
      :models="models ?? []"
      @saved="refreshAll"
      @delete="handleDeleteAgentClick"
      @navigate="moveInPanel"
    />

    <!-- Create Agent Modal -->
    <AgentsCreateAgentModal
      v-model:open="showCreateAgentModal"
      :available-prompt-versions="allPromptVersions ?? []"
      :available-models="models ?? []"
      :loading="creatingAgent"
      @submit="handleCreateAgent"
    />

    <!-- Delete Agent Modal -->
    <BaseConfirmDialog
      v-model:open="showDeleteAgentModal"
      :title="`Delete “${selectedAgent?.name}”?`"
      message="An agent that experiments use can’t be deleted. This can’t be undone."
      confirm-label="Delete"
      variant="error"
      :loading="deletingAgent"
      @confirm="handleDeleteAgent"
      @after-leave="selectedAgent = null"
    />
  </BasePageContent>
</template>
