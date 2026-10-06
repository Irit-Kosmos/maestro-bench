<script setup lang="ts">
import type { Agent, AgentKind, AgentTeam, Model, PromptVersion, Tag } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import { h, resolveComponent } from 'vue'
import { useGroupBy } from '~/composables/useGroupBy'
import { byOrder } from '~/utils/filters'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'

// Composables
const { showCreateSuccess, showCreateError, showDeleteSuccess, showDeleteError, ok } = useStandardToast()
const { createTeam } = useAgentTeams()
const { createAgent, deleteAgent } = useAgents()
const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

// Fetch data directly in the page
const { data: agentTeams, pending, error: teamsError, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, error: agentsError, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: allPromptVersions, pending: _promptVersionsPending } = await useMyLazyFetch<PromptVersion[]>('/prompt-versions')
const { data: models, pending: _modelsPending } = await useMyLazyFetch<Model[]>('/models')

function reloadAgents() {
  refreshTeams()
  refreshAgents()
}

// Page meta
definePageMeta({
  title: 'Agents',
})

useSeoMeta({
  title: 'Agents',
  description: 'Manage your AI agents and aggregators and organize them into teams for coordinated experiments.',
})

// Modal states
const showCreateTeamModal = ref(false)
const showCreateAgentModal = ref(false)
const showDeleteAgentModal = ref(false)
const creatingTeam = ref(false)
const creatingAgent = ref(false)
const deletingAgent = ref(false)

// Agent targeted by the delete confirmation
const selectedAgent = ref<Agent | null>(null)

// An agent as a row: the API returns ids, so the names the table shows and searches are resolved here
interface AgentRow extends Agent {
  kind: AgentKind
  tags: Tag[]
  team_name: string
  team_description: string | null
  prompt_label: string | null
  model: Model | null
}

const rows = computed<AgentRow[]>(() => {
  const teams = new Map((agentTeams.value ?? []).map(team => [team.id, team]))
  const versions = new Map((allPromptVersions.value ?? []).map(version => [version.id, version]))
  const modelsById = new Map((models.value ?? []).map(model => [model.id, model]))
  return (agents.value ?? [])
    .map((agent) => {
      const team = teams.get(agent.team_id)
      const version = agent.default_prompt_version_id == null ? undefined : versions.get(agent.default_prompt_version_id)
      return {
        ...agent,
        kind: agent.kind ?? 'llm',
        tags: agent.tags ?? [],
        team_name: team?.name ?? '',
        team_description: team?.description ?? null,
        prompt_label: version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null,
        model: agent.default_model_id == null ? null : modelsById.get(agent.default_model_id) ?? null,
      }
    })
    .sort((a, b) => a.team_name.localeCompare(b.team_name) || a.name.localeCompare(b.name))
})

// Table
const UIcon = resolveComponent('UIcon')

const columns = [
  {
    key: 'name',
    // The one column without a width: it takes what the others leave, so the description gets room
    label: 'Agent',
    formatter: (_: unknown, row: AgentRow) => `${row.name} ${row.description ?? ''}`,
    render: (row: AgentRow) => h('span', { class: 'flex min-h-9 min-w-0 items-center gap-3' }, [
      // The tile is what tells an aggregator from a model call at a glance
      h('span', {
        'class': ['flex size-7 shrink-0 items-center justify-center rounded-md', row.kind === 'aggregator' ? 'bg-info/10 text-info' : 'bg-elevated text-muted'],
        'aria-hidden': 'true',
      }, [h(UIcon, { name: row.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-ghost-bold', class: 'size-4' })]),
      h('span', { class: 'flex min-w-0 flex-col' }, [
        h('span', { class: 'truncate leading-5' }, row.name),
        row.description ? h('span', { class: 'truncate text-xs font-normal leading-4 text-muted', title: row.description }, row.description) : null,
      ]),
    ]),
  },
  { key: 'kind', width: 136, label: 'Type', formatter: (_: unknown, row: AgentRow) => row.kind === 'aggregator' ? 'Aggregator' : 'LLM' },
  { key: 'team_id', width: 150, label: 'Team', formatter: (_: unknown, row: AgentRow) => row.team_name },
  { key: 'default_prompt_version_id', width: 170, label: 'Prompt', formatter: (_: unknown, row: AgentRow) => row.prompt_label ?? '' },
  { key: 'default_model_id', width: 180, label: 'Model', formatter: (_: unknown, row: AgentRow) => row.model?.name ?? '' },
  {
    key: 'tags',
    width: 200,
    label: 'Tags',
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, row: AgentRow) => row.tags.map(tag => tag.name).join(' '),
  },
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
    key: 'team',
    label: 'Team',
    icon: 'i-ph-users-three-bold',
    plural: 'teams',
    searchPlaceholder: 'Search a team…',
    value: agent => agent.team_name,
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

// Sections the list can be cut into; the choice is remembered per browser. Teams first, as the page used to be
const groups: GroupSpec<AgentRow>[] = [
  {
    key: 'team',
    label: 'Team',
    icon: 'i-ph-users-three-bold',
    value: agent => agent.team_name,
    hint: name => rows.value.find(agent => agent.team_name === name)?.team_description,
  },
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
const groupBy = useGroupBy('maestro:agents-group-by', 'team')

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
  await Promise.all([refreshAgents(), refreshTeams()]) // Teams include their agents
}

useCreateFromQuery(() => {
  showCreateAgentModal.value = true
})

// Handlers
function handleDeleteAgentClick(agent: Agent) {
  selectedAgent.value = agent
  showDeleteAgentModal.value = true
}

async function handleCreateTeam(data: any) {
  creatingTeam.value = true
  const result = await createTeam(data)
  creatingTeam.value = false
  if (result.success) {
    showCreateTeamModal.value = false
    showCreateSuccess('Team', { description: 'It shows up here once it has an agent.' })
    await refreshTeams()
  }
  else {
    showCreateError('Team', result.error)
  }
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
    :loading="pending && agentsPending && !agents"
    :error="(!agents && !!agentsError) || (!agentTeams && !!teamsError)"
    :error-kind="fetchErrorKind(agentsError ?? teamsError)"
    @retry="reloadAgents"
  >
    <template #before-content>
      <UIGuardedButton
        variant="soft"
        color="neutral"
        icon="i-ph-users-three-bold"
        size="sm"
        @click="() => { showCreateTeamModal = true }"
      >
        New team
      </UIGuardedButton>
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
      :data="rows"
      :columns="columns"
      :filters="filters"
      :groups="groups"
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

      <template #team_id-cell="{ row }">
        <span class="block truncate text-sm text-toned" :title="row.original.team_description ?? undefined">{{ row.original.team_name }}</span>
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
          selectable
          @changed="refreshAgents"
          @select="tag => { filterState = filterByTag(filterState, tag.name) }"
        />
      </template>

      <template #created_at-cell="{ row }">
        <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.created_at)">
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
      :teams="agentTeams ?? []"
      :prompt-versions="allPromptVersions ?? []"
      :models="models ?? []"
      @saved="refreshAll"
      @delete="handleDeleteAgentClick"
      @navigate="moveInPanel"
    />

    <!-- Create Team Modal -->
    <AgentsCreateTeamModal
      v-model:open="showCreateTeamModal"
      :available-agents="agents ?? []"
      :loading="creatingTeam"
      @submit="handleCreateTeam"
    />

    <!-- Create Agent Modal -->
    <AgentsCreateAgentModal
      v-model:open="showCreateAgentModal"
      :available-teams="agentTeams ?? []"
      :available-prompt-versions="allPromptVersions ?? []"
      :available-models="models ?? []"
      :loading="creatingAgent"
      @submit="handleCreateAgent"
    />

    <!-- Delete Agent Modal -->
    <BaseConfirmDialog
      v-model:open="showDeleteAgentModal"
      :title="`Delete “${selectedAgent?.name}”?`"
      message="It is removed from its team and from the experiment configurations that use it. This can’t be undone."
      confirm-label="Delete"
      variant="error"
      :loading="deletingAgent"
      @confirm="handleDeleteAgent"
      @after-leave="selectedAgent = null"
    />
  </BasePageContent>
</template>
