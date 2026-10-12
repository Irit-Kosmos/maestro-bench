<script setup lang="ts">
import type { Agent, AgentConfiguration, Model, PromptVersion } from '~/types'

// Agents of the experiment. The backend runs them one after another and returns the last one's output,
// so the default view is an ordered list. The graph is kept for those who prefer to wire agents visually.
const props = defineProps<{
  agents?: Agent[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  datasetHeaders?: readonly string[]
  /** Variables of the prompt variations, per agent: they keep their mappings */
  extraVariables?: Record<number, readonly string[]>
  /** Reloads the agents, so an agent created here can be added */
  refreshAgents?: () => Promise<void>
}>()

const emit = defineEmits<{
  openPromptDetails: [promptVersionId: number]
}>()

const configurations = defineModel<Record<number, AgentConfiguration>>('agentConfigurations', { required: true })

const { info } = useStandardToast()

const models = computed(() => props.models ?? [])
const promptVersions = computed(() => props.allPromptVersions ?? [])
const datasetHeaders = computed(() => props.datasetHeaders ?? [])

const pipeline = useAgentPipeline({
  agents: computed(() => props.agents),
  configurations,
  promptVersions,
  datasetHeaders,
  extraVariables: computed(() => props.extraVariables ?? {}),
})
const { items } = pipeline

// Output paths and previews follow the prompt version each agent runs with here
provide(AGENT_PROMPT_VERSIONS, computed(() => Object.fromEntries(Object.entries(configurations.value)
  .map(([id, config]) => [Number(id), config?.prompt_version_id]))))

const view = ref<'list' | 'graph'>('list')
const flowViewRef = ref<{ computeExecutionOrder: () => Map<number, number>, addAgent: (agent: Agent) => void } | null>(null)

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
      info('Agents now run in list order', 'Agents that were not connected to each other run one after another.')
    }
  }
  view.value = next
}

// --- Adding agents ---

const { canEdit } = useCurrentWorkspace()

const hasAgents = computed(() => (props.agents?.length ?? 0) > 0)

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
  // An agent created a moment ago comes from the reloaded agents
  const known = pipeline.catalog.value.get(agent.id) ?? agent
  if (view.value === 'graph' && flowViewRef.value) {
    flowViewRef.value.addAgent(known)
    return
  }
  pipeline.add(known)
  // A new agent is what the eyes are on: open it and fold the others. A lone agent is already a form.
  openIds.value = new Set([known.id])
}

const pickerProps = computed(() => ({
  agents: props.agents,
  models: models.value,
  promptVersions: promptVersions.value,
  addedIds: pipeline.addedIds.value,
  refreshAgents: props.refreshAgents,
}))

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

function syncMappings() {
  // The graph owns the order while it is shown, so only fill in what it can't break
  if (view.value === 'graph')
    pipeline.autoMapAll()
  else
    pipeline.syncAll()
}

watch(datasetHeaders, syncMappings, { immediate: true })

// A prompt variation brings variables of its own, and drops them when it is removed
watch(() => props.extraVariables, syncMappings, { deep: true })

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

// Said once, whatever is chosen, so the section doesn't change under the eyes
const description = 'What runs on each row. Chain several: they run in order, and the last output is the result.'

const emptyText = computed(() => {
  if (!props.agents)
    return 'Loading agents…'
  if (!hasAgents.value)
    return canEdit.value ? 'No agents yet. Type a name above to create one.' : 'No agents in this workspace yet.'
  return canEdit.value ? 'No agent yet. Pick one above, or type a new name to create it.' : 'No agent yet. Pick one above.'
})

const problems = computed(() => items.value
  .map(item => ({ item, issues: pipeline.issuesOf(item.agent.id) }))
  .filter(entry => entry.issues.length > 0))
const problemCount = computed(() => problems.value.reduce((total, entry) => total + entry.issues.length, 0))
</script>

<template>
  <ExperimentsSection id="agents" title="Agents" :description="description">
    <!-- Offered from the start: one agent can still be better read as a graph -->
    <template #actions>
      <UTabs
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

    <div class="flex flex-col gap-4">
      <!-- Always there, in both views and whatever is chosen: the one place to add or create an agent -->
      <div class="flex">
        <ExperimentsAgentPicker v-bind="pickerProps" @add="addAgent" />
      </div>

      <!-- List view -->
      <div v-if="view === 'list'" ref="listRef" class="flex flex-col gap-4">
        <p v-if="items.length === 0" class="rounded-lg border border-dashed border-default px-4 py-3 text-sm text-muted">
          {{ emptyText }}
        </p>

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
        :agents="agents"
        :models="models"
        :all-prompt-versions="promptVersions"
        :agent-configurations="configurations"
        :dataset-headers="datasetHeaders"
        @update-agent-config="onGraphUpdate"
        @remove-agent-config="id => pipeline.remove(id)"
        @add-agent="id => nextTick(() => pipeline.autoMap(id))"
        @open-prompt-details="id => emit('openPromptDetails', id)"
      >
        <template #tools="{ settled }">
          <ExperimentsAgentPicker v-if="settled" v-bind="pickerProps" @add="addAgent" />
        </template>
      </ExperimentsAgentFlowView>

      <p class="sr-only" role="status">
        {{ announcement }}
      </p>
    </div>
  </ExperimentsSection>
</template>
