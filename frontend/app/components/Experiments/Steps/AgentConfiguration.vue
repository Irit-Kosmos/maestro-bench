<script setup lang="ts">
import type { Agent, AgentConfiguration, AgentTeam, CreateAgentForm, Model, PromptVersion } from '~/types'

// Agents of the experiment. The backend runs them one after another and returns the last one's output,
// so the default view is an ordered list. The graph is kept for those who prefer to wire agents visually.
const props = defineProps<{
  agentTeams?: AgentTeam[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  datasetHeaders?: readonly string[]
  /** Reloads the agent teams, so an agent created here can be added */
  refreshAgents?: () => Promise<void>
}>()

const emit = defineEmits<{
  openPromptDetails: [promptVersionId: number]
}>()

const configurations = defineModel<Record<number, AgentConfiguration>>('agentConfigurations', { required: true })

const toast = useToast()

const models = computed(() => props.models ?? [])
const promptVersions = computed(() => props.allPromptVersions ?? [])
const datasetHeaders = computed(() => props.datasetHeaders ?? [])

const pipeline = useAgentPipeline({
  agentTeams: computed(() => props.agentTeams),
  configurations,
  promptVersions,
  datasetHeaders,
})
const { items } = pipeline

// Output paths and previews follow the prompt version each agent runs with here
provide(AGENT_PROMPT_VERSIONS, computed(() => Object.fromEntries(Object.entries(configurations.value)
  .map(([id, config]) => [Number(id), config?.prompt_version_id]))))

const view = ref<'list' | 'graph'>('list')
const flowViewRef = ref<{ computeExecutionOrder: () => Map<number, number> } | null>(null)

// One agent has nothing to order or wire: the graph is only offered from two
watch(() => items.value.length, (count) => {
  if (count < 2 && view.value === 'graph')
    view.value = 'list'
})

// Run order for submission: the graph's topological order, or simply the list's
function getExecutionOrder() {
  if (view.value === 'graph' && flowViewRef.value)
    return flowViewRef.value.computeExecutionOrder()
  return new Map(items.value.map(item => [item.agent.id, item.position]))
}

defineExpose({ getExecutionOrder })

// --- View switch ---

const viewOptions = [
  { value: 'list', label: 'List', icon: 'i-ph-list-numbers-bold' },
  { value: 'graph', label: 'Graph', icon: 'i-ph-git-branch-bold' },
]

function showView(next: 'list' | 'graph') {
  if (next === view.value)
    return
  if (next === 'list' && flowViewRef.value) {
    // The list has one order: connected agents keep theirs, unconnected ones follow the list
    const order = flowViewRef.value.computeExecutionOrder()
    const hasTies = new Set(order.values()).size < order.size
    pipeline.applyOrder(order)
    if (hasTies) {
      toast.add({
        title: 'Agents now run in list order',
        description: 'Agents that were not connected to each other run one after another.',
        icon: 'i-ph-info-bold',
      })
    }
  }
  view.value = next
}

// --- Adding agents ---

const pickerItems = computed<any[]>(() => (props.agentTeams ?? []).flatMap((team) => {
  const available = (team.agents ?? []).filter(agent => !pipeline.addedIds.value.has(agent.id))
  if (available.length === 0)
    return []
  return [
    { type: 'label' as const, label: team.name },
    ...available.map(agent => ({ label: agent.name, value: agent.id })),
  ]
}))

const hasAgents = computed(() => (props.agentTeams ?? []).some(team => (team.agents?.length ?? 0) > 0))
const allAdded = computed(() => hasAgents.value && pickerItems.value.length === 0)

const openIds = ref(new Set<number>())

function setOpen(id: number, value: boolean) {
  const next = new Set(openIds.value)
  if (value)
    next.add(id)
  else
    next.delete(id)
  openIds.value = next
}

function addAgent(agent: Agent) {
  pipeline.add(agent)
  // A new agent is what the eyes are on: open it and fold the others. A lone agent is already a form.
  openIds.value = new Set([agent.id])
}

// The menu is only a way to add: it never keeps a selection
const picked = ref<number>()

function addById(id: number | undefined) {
  const agent = id === undefined ? undefined : pipeline.catalog.value.get(id)?.agent
  if (agent)
    addAgent(agent)
  nextTick(() => {
    picked.value = undefined
  })
}

// The agents of a team, as the first-time choice
const teamGroups = computed(() => (props.agentTeams ?? [])
  .filter(team => (team.agents?.length ?? 0) > 0)
  .map(team => ({ team, agents: team.agents })))

function defaultSummary(agent: Agent) {
  if (agent.kind === 'aggregator')
    return 'Aggregator'
  const version = promptVersions.value.find(v => v.id === agent.default_prompt_version_id)
  const model = models.value.find(m => m.id === agent.default_model_id)
  return [
    version ? `${version.prompt?.name || 'Unknown'} v${version.version}` : null,
    model?.name,
  ].filter(Boolean).join(' · ')
}

// --- Creating an aggregator on the spot ---

const { createAgent } = useAgents()
const showCreateAggregator = ref(false)

// The team of the agents it will most likely read
const aggregatorTeamId = computed(() => items.value.at(-1)?.agent.team_id)

async function createAggregator(data: CreateAgentForm) {
  const result = await createAgent(data)
  if (!result.success) {
    toast.add({ title: 'Could not create the aggregator', description: result.error, color: 'error', icon: 'i-ph:x-bold' })
    return
  }
  await props.refreshAgents?.()
  const created = result.data as Agent
  const agent = pipeline.catalog.value.get(created.id)?.agent ?? created
  addAgent(agent)
}

// --- Reordering ---

const listRef = ref<HTMLElement | null>(null)
const sortableRef = ref<HTMLElement | null>(null)
const announcement = ref('')

// Dragging is the main way; the grip also answers the arrow keys, for those who don't use a pointer
useSortableList(sortableRef, {
  onMove: (from, to) => {
    const item = items.value[from]
    if (item && pipeline.moveTo(item.agent.id, to))
      announce(item.agent.id)
  },
})

function announce(agentId: number) {
  const item = items.value.find(i => i.agent.id === agentId)
  announcement.value = item ? `${item.agent.name} is now step ${item.position} of ${items.value.length}` : ''
}

async function move(agentId: number, delta: -1 | 1) {
  if (!pipeline.move(agentId, delta))
    return
  announce(agentId)
  // Reordering re-inserts the row, which drops focus: put it back on the grip that was used
  await nextTick()
  listRef.value?.querySelector<HTMLButtonElement>(`[data-drag-handle="${agentId}"]`)?.focus()
}

function removeAgent(agent: Agent) {
  const name = agent.name
  pipeline.remove(agent.id)
  announcement.value = `${name} removed`
}

// --- Keeping mappings in step with the dataset ---

watch(datasetHeaders, () => {
  // The graph owns the order while it is shown, so only fill in what it can't break
  if (view.value === 'graph')
    pipeline.autoMapAll()
  else
    pipeline.syncAll()
}, { immediate: true })

// Coming back to this step: open the agents that still need something
onMounted(() => {
  if (items.value.length > 1) {
    openIds.value = new Set(items.value.filter(item => pipeline.issuesOf(item.agent.id).length > 0).map(item => item.agent.id))
  }
})

// Graph events
function onGraphUpdate(agentId: number, field: string) {
  if (field === 'prompt_version_id' || field === 'reset')
    nextTick(() => pipeline.autoMap(agentId))
}

const description = computed(() => {
  if (items.value.length === 0)
    return 'Choose the agent to run on each row. You can add more afterwards to chain them.'
  if (items.value.length === 1)
    return 'Set its prompt and model, and where each variable of the prompt gets its value.'
  return view.value === 'list'
    ? 'Agents run from top to bottom and can read the output of the ones above. The last agent\'s output is the result.'
    : 'Connect agents to set the order they run in. The last one\'s output is the result.'
})

const problems = computed(() => items.value
  .map(item => ({ item, issues: pipeline.issuesOf(item.agent.id) }))
  .filter(entry => entry.issues.length > 0))
const problemCount = computed(() => problems.value.reduce((total, entry) => total + entry.issues.length, 0))
</script>

<template>
  <ExperimentsSection id="agents" title="Agents" :description="description">
    <template v-if="items.length > 0" #actions>
      <UTabs
        v-if="items.length > 1"
        :model-value="view"
        :items="viewOptions"
        :content="false"
        variant="pill"
        color="neutral"
        size="xs"
        :ui="{
          indicator: 'bg-default ring ring-default shadow-xs',
          trigger: 'data-[state=active]:text-highlighted',
        }"
        aria-label="View"
        @update:model-value="value => showView(value as 'list' | 'graph')"
      />
    </template>

    <!-- Nothing chosen yet -->
    <div v-if="items.length === 0">
      <div v-if="hasAgents" class="flex flex-col gap-4">
        <div v-for="group in teamGroups" :key="group.team.id">
          <h3 class="mb-1.5 text-xs font-medium text-muted">
            {{ group.team.name }}
          </h3>
          <ul class="flex flex-col gap-2">
            <li v-for="agent in group.agents" :key="agent.id">
              <!-- Native button: a full-width row shouldn't inherit the press scale of UButton -->
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-lg border border-default px-4 py-3 text-left outline-none hover:border-accented hover:bg-elevated/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inverted"
                @click="addAgent(agent)"
              >
                <UIcon :name="agent.kind === 'aggregator' ? 'i-ph-function-bold' : 'i-ph-robot-bold'" class="size-4 shrink-0 text-muted" aria-hidden="true" />
                <span class="min-w-0 flex-1">
                  <span class="block truncate text-sm font-medium text-highlighted">{{ agent.name }}</span>
                  <span v-if="agent.description" class="mt-0.5 block truncate text-sm text-muted">{{ agent.description }}</span>
                </span>
                <span v-if="defaultSummary(agent)" class="hidden shrink-0 text-xs text-toned md:block">{{ defaultSummary(agent) }}</span>
                <UIcon name="i-ph-plus-bold" class="size-4 shrink-0 text-muted" aria-hidden="true" />
              </button>
            </li>
          </ul>
        </div>
      </div>

      <BaseEmptyState
        v-else-if="agentTeams"
        icon="i-ph-robot-bold"
        title="No agents yet"
        message="Create an agent first, then come back to create the experiment."
        action-label="New agent"
        action-to="/agents"
      />

      <BaseLoadingState v-else message="Loading agents…" />
    </div>

    <div v-else class="flex flex-col gap-4">
      <!-- List view -->
      <div v-if="view === 'list'" ref="listRef" class="flex flex-col gap-4">
        <div class="flex flex-wrap items-center gap-2">
          <USelectMenu
            v-if="!allAdded"
            v-model="picked"
            value-key="value"
            :items="pickerItems"
            :ui="{ content: 'min-w-60' }"
            icon="i-ph-plus-bold"
            placeholder="Add an agent"
            :search-input="{ placeholder: 'Search agents…' }"
            class="w-full sm:w-64"
            aria-label="Add an agent"
            @update:model-value="(id) => addById(id as number | undefined)"
          />
          <UButton
            color="neutral"
            variant="ghost"
            size="sm"
            icon="i-ph-function-bold"
            title="Combine the outputs of the agents above with formulas, like a weighted score"
            @click="() => { showCreateAggregator = true }"
          >
            New aggregator
          </UButton>
        </div>

        <div
          v-if="items.length > 1"
          ref="sortableRef"
          class="divide-y divide-default overflow-hidden rounded-lg border border-default"
        >
          <ExperimentsAgentListItem
            v-for="item in items"
            :key="item.agent.id"
            :item="item"
            :count="items.length"
            :models="models"
            :prompt-versions="promptVersions"
            :dataset-headers="datasetHeaders"
            :upstream-agents="pipeline.upstreamOf(item.agent.id)"
            :issues="pipeline.issuesOf(item.agent.id)"
            :open="openIds.has(item.agent.id)"
            @update:open="(value: boolean) => setOpen(item.agent.id, value)"
            @update="(field, value) => pipeline.update(item.agent.id, field, value)"
            @set-mapping="mapping => pipeline.setMapping(item.agent.id, mapping)"
            @open-prompt-details="id => emit('openPromptDetails', id)"
            @move="delta => move(item.agent.id, delta)"
            @remove="removeAgent(item.agent)"
            @reset="pipeline.reset(item.agent.id)"
          />
        </div>

        <div v-else>
          <ExperimentsAgentListItem
            v-for="item in items"
            :key="item.agent.id"
            :item="item"
            :count="1"
            :models="models"
            :prompt-versions="promptVersions"
            :dataset-headers="datasetHeaders"
            :upstream-agents="[]"
            :issues="pipeline.issuesOf(item.agent.id)"
            @update="(field, value) => pipeline.update(item.agent.id, field, value)"
            @set-mapping="mapping => pipeline.setMapping(item.agent.id, mapping)"
            @open-prompt-details="id => emit('openPromptDetails', id)"
            @remove="removeAgent(item.agent)"
            @reset="pipeline.reset(item.agent.id)"
          />
        </div>

        <!-- What still blocks "Create and start": a count, then the issues grouped by agent -->
        <section
          v-if="problems.length > 0"
          class="rounded-lg border border-warning/30 bg-warning/5 px-4 py-3"
          aria-labelledby="agents-problems-title"
        >
          <h3 id="agents-problems-title" class="flex items-center gap-2 text-sm font-medium text-highlighted">
            <UIcon name="i-ph-warning-bold" class="size-4 shrink-0 text-warning" aria-hidden="true" />
            {{ problemCount }} {{ problemCount === 1 ? 'thing' : 'things' }} to fix before creating
          </h3>
          <ul class="mt-2 flex flex-col gap-2 ps-6">
            <li v-for="entry in problems" :key="entry.item.agent.id" class="text-sm">
              <template v-if="items.length > 1">
                <button
                  type="button"
                  class="rounded-sm font-medium text-highlighted underline-offset-2 outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inverted"
                  @click="setOpen(entry.item.agent.id, true)"
                >
                  {{ entry.item.agent.name }}
                </button>
              </template>
              <ul class="list-disc ps-4 text-muted marker:text-warning" :class="{ 'mt-0.5': items.length > 1 }">
                <li v-for="issue in entry.issues" :key="issue">
                  {{ issue }}
                </li>
              </ul>
            </li>
          </ul>
        </section>
      </div>

      <!-- Graph view -->
      <ExperimentsAgentFlowView
        v-else
        ref="flowViewRef"
        :agent-teams="agentTeams"
        :models="models"
        :all-prompt-versions="promptVersions"
        :agent-configurations="configurations"
        :dataset-headers="datasetHeaders"
        @update-agent-config="onGraphUpdate"
        @remove-agent-config="id => pipeline.remove(id)"
        @add-agent="id => nextTick(() => pipeline.autoMap(id))"
        @open-prompt-details="id => emit('openPromptDetails', id)"
      />

      <p class="sr-only" role="status">
        {{ announcement }}
      </p>
    </div>

    <AgentsCreateAgentModal
      v-model:open="showCreateAggregator"
      :available-teams="agentTeams ?? []"
      initial-kind="aggregator"
      lock-kind
      :initial-team-id="aggregatorTeamId"
      @submit="createAggregator"
    />
  </ExperimentsSection>
</template>
