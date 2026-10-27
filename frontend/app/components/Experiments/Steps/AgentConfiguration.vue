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
import type { PipelineItem } from '~/composables/useAgentPipeline'
import type { Agent, AgentConfiguration, Model, PromptVersion } from '~/types'

// Steps of the experiment: runs of an agent, which may run more than once. The backend runs them one after another
// and returns the last one's output, so the default view is an ordered list. The graph is kept for those who prefer
// to wire agents visually.
const props = defineProps<{
  agents?: Agent[] | null
  models?: Model[] | null
  allPromptVersions?: PromptVersion[] | null
  datasetHeaders?: readonly string[]
  /** Variables of the prompt variations, per step key: they keep their mappings */
  extraVariables?: Record<string, readonly string[]>
  /** Reloads the agents, so an agent created here can be added */
  refreshAgents?: () => Promise<void>
}>()

const emit = defineEmits<{
  openPromptDetails: [promptVersionId: number]
}>()

const configurations = defineModel<Record<string, AgentConfiguration>>('agentConfigurations', { required: true })

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

// Output paths and previews follow the prompt version each step runs with here
provide(AGENT_PROMPT_VERSIONS, computed(() => Object.fromEntries(Object.entries(configurations.value)
  .map(([key, config]) => [key, config?.prompt_version_id]))))

const view = ref<'list' | 'graph'>('list')
const flowViewRef = ref<{ computeExecutionOrder: () => Map<string, number>, addAgent: (agent: Agent) => void } | null>(null)

// Run order for submission: the graph's topological order, or simply the list's
function getExecutionOrder() {
  if (view.value === 'graph' && flowViewRef.value)
    return flowViewRef.value.computeExecutionOrder()
  return new Map(items.value.map(item => [item.key, item.position]))
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

const openKeys = ref(new Set<string>())

function setOpen(key: string, value: boolean) {
  const next = new Set(openKeys.value)
  if (value)
    next.add(key)
  else
    next.delete(key)
  openKeys.value = next
}

function addAgent(agent: Agent) {
  // An agent created a moment ago comes from the reloaded agents
  const known = pipeline.catalog.value.get(agent.id) ?? agent
  if (view.value === 'graph' && flowViewRef.value) {
    flowViewRef.value.addAgent(known)
    return
  }
  const key = pipeline.add(known)
  // A new step is what the eyes are on: open it and fold the others. A lone step is already a form.
  openKeys.value = new Set([key])
}

const pickerProps = computed(() => ({
  agents: props.agents,
  models: models.value,
  promptVersions: promptVersions.value,
  addedCounts: pipeline.addedCounts.value,
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
    if (item && pipeline.moveTo(item.key, to))
      announce(item.key)
  },
})

function announce(key: string) {
  const item = items.value.find(i => i.key === key)
  announcement.value = item ? `${item.label} is now step ${item.position} of ${items.value.length}` : ''
}

async function move(key: string, delta: -1 | 1) {
  if (!pipeline.move(key, delta))
    return
  announce(key)
  // Reordering re-inserts the row, which drops focus: put it back on the grip that was used
  await nextTick()
  listRef.value?.querySelector<HTMLButtonElement>(`[data-drag-handle="${key}"]`)?.focus()
}

function removeStep(item: PipelineItem) {
  const label = item.label
  pipeline.remove(item.key)
  announcement.value = `${label} removed`
}

// A node removed from the graph: the graph has already dropped the mappings that read it.
// Its order is the graph's, so the list's renumbering and pruning would drop mappings to
// steps the graph runs earlier but the list holds further down
function removeGraphStep(key: string) {
  delete configurations.value[key]
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
    openKeys.value = new Set(items.value.filter(item => pipeline.issuesOf(item.key).length > 0).map(item => item.key))
  }
})

// Graph events
function onGraphUpdate(key: string, field: string) {
  if (field === 'prompt_version_id' || field === 'reset')
    nextTick(() => pipeline.autoMap(key))
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
  .map(item => ({ item, issues: pipeline.issuesOf(item.key) }))
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
            :key="item.key"
            :item="item"
            :count="items.length"
            :models="models"
            :prompt-versions="promptVersions"
            :dataset-headers="datasetHeaders"
            :upstream-steps="pipeline.upstreamOf(item.key)"
            :issues="pipeline.issuesOf(item.key)"
            :open="openKeys.has(item.key)"
            @update:open="(value: boolean) => setOpen(item.key, value)"
            @update="(field, value) => pipeline.update(item.key, field, value)"
            @set-mapping="mapping => pipeline.setMapping(item.key, mapping)"
            @open-prompt-details="id => emit('openPromptDetails', id)"
            @move="delta => move(item.key, delta)"
            @remove="removeStep(item)"
            @reset="pipeline.reset(item.key)"
          />
        </div>

        <div v-else>
          <ExperimentsAgentListItem
            v-for="item in items"
            :key="item.key"
            :item="item"
            :count="1"
            :models="models"
            :prompt-versions="promptVersions"
            :dataset-headers="datasetHeaders"
            :upstream-steps="[]"
            :issues="pipeline.issuesOf(item.key)"
            @update="(field, value) => pipeline.update(item.key, field, value)"
            @set-mapping="mapping => pipeline.setMapping(item.key, mapping)"
            @open-prompt-details="id => emit('openPromptDetails', id)"
            @remove="removeStep(item)"
            @reset="pipeline.reset(item.key)"
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
            <li v-for="entry in problems" :key="entry.item.key" class="text-sm">
              <template v-if="items.length > 1">
                <button
                  type="button"
                  class="rounded-sm font-medium text-highlighted underline-offset-2 outline-none hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inverted"
                  @click="setOpen(entry.item.key, true)"
                >
                  {{ entry.item.label }}
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
        @remove-agent-config="removeGraphStep"
        @add-agent="key => nextTick(() => pipeline.autoMap(key))"
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
