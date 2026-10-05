<script setup lang="ts">
import type { AnalysisForm, AnalysisRunRef, AnalysisValueType, AvailableExecution, ExecutionFields, MetricInfo } from '~/types'

const form = defineModel<AnalysisForm>({ required: true })

const { fetchExecutionFields } = useAnalyses()
const { formatShortDate } = useUIHelpers()

const { data: executions } = await useMyLazyFetch<AvailableExecution[]>('/analyses/executions')
const { data: metrics } = await useMyLazyFetch<MetricInfo[]>('/analyses/metrics')

// Columns and output paths per execution, read from its results file
const fields = ref<Record<number, ExecutionFields>>({})

async function loadFields(executionId: number) {
  if (fields.value[executionId])
    return
  try {
    fields.value[executionId] = await fetchExecutionFields(executionId)
  }
  catch (error) {
    console.error('Error fetching execution fields:', error)
  }
}

const columns = computed(() => {
  const all = new Set<string>()
  for (const run of form.value.runs)
    fields.value[run.execution_id]?.columns.forEach(c => all.add(c))
  return [...all]
})

const pathSuggestions = computed(() => {
  const all = new Set<string>()
  for (const run of form.value.runs) {
    const agent = fields.value[run.execution_id]?.agents.find(a => a.name === run.agent_name)
    agent?.paths.forEach(p => all.add(p))
  }
  return [...all]
})

watch(
  () => form.value.runs.map(r => r.execution_id),
  async (ids) => {
    await Promise.all(ids.map(loadFields))
    applyDefaults()
  },
  { immediate: true },
)

// Fill what can be inferred once an execution's fields are known: the last
// agent of the pipeline, and the first output path when none is set
function applyDefaults() {
  for (const run of form.value.runs) {
    const agents = fields.value[run.execution_id]?.agents ?? []
    if (!run.agent_name && agents.length)
      run.agent_name = [...agents].sort((a, b) => b.execution_order - a.execution_order)[0]!.name
  }
  if (!form.value.config.output_path) {
    const first = pathSuggestions.value[0]
    if (first)
      form.value.config.output_path = first
  }
}

// --- Title ---

const nameInput = useTemplateRef<HTMLInputElement>('nameInput')
onMounted(() => {
  if (!form.value.name)
    nameInput.value?.focus()
})

// --- Executions ---

function executionOf(executionId: number) {
  return executions.value?.find(e => e.execution_id === executionId)
}

const executionItems = computed(() => (executions.value ?? []).map(e => ({
  label: `#${e.execution_id} · ${e.experiment_name}`,
  description: [e.dataset_name, e.agents.map(a => a.model).join(', '), formatShortDate(e.started_at)]
    .filter(Boolean)
    .join(' · '),
  value: e.execution_id,
  rows: e.row_count,
})))

// The picker toggles executions: checking adds a run, unchecking drops every run of that execution
const pickedExecutions = computed<number[]>({
  get: () => [...new Set(form.value.runs.map(r => r.execution_id))],
  set: (ids) => {
    const wanted = new Set(ids)
    const kept = form.value.runs.filter(r => wanted.has(r.execution_id))
    const present = new Set(kept.map(r => r.execution_id))
    const added: AnalysisRunRef[] = ids
      .filter(id => !present.has(id))
      .map(id => ({ execution_id: id, agent_name: '', label: null }))
    form.value.runs = [...kept, ...added]
  },
})

function agentsOf(executionId: number) {
  return fields.value[executionId]?.agents ?? []
}

function agentItems(executionId: number) {
  return agentsOf(executionId).map(a => ({
    label: a.model ? `${a.name} (${a.model})` : a.name,
    value: a.name,
  }))
}

// The model behind the agent whose output is compared
function modelOf(run: AnalysisRunRef) {
  const agents = agentsOf(run.execution_id)
  return (agents.find(a => a.name === run.agent_name) ?? agents[0])?.model ?? null
}

// Renaming happens in place, on one row at a time
const renaming = ref<number | null>(null)
const vFocus = { mounted: (el: HTMLElement) => el.focus() }

function stopRenaming(run: AnalysisRunRef) {
  run.label = null
  renaming.value = null
}

function removeRun(index: number) {
  form.value.runs.splice(index, 1)
}

// The order of the runs is the order of the comparison: dragged by the grip, or moved with its arrow keys
const runList = useTemplateRef<HTMLElement>('runList')

function moveRunTo(from: number, to: number) {
  const runs = form.value.runs
  if (to < 0 || to >= runs.length || from === to)
    return
  const [run] = runs.splice(from, 1)
  runs.splice(to, 0, run!)
}

useSortableList(runList, { onMove: moveRunTo })

async function moveRun(run: AnalysisRunRef, offset: -1 | 1) {
  moveRunTo(form.value.runs.indexOf(run), form.value.runs.indexOf(run) + offset)
  // The row is re-inserted, which drops focus: put it back on its grip
  await nextTick()
  runList.value?.querySelector<HTMLButtonElement>(`[data-drag-handle="${runKey(run)}"]`)?.focus()
}

// A row keeps its identity when it moves, so its key can't be its index
const runKeys = new WeakMap<AnalysisRunRef, number>()
let nextRunKey = 0

function runKey(run: AnalysisRunRef) {
  if (!runKeys.has(run))
    runKeys.set(run, nextRunKey++)
  return runKeys.get(run)!
}

// An execution with several agents can be compared once per agent
function canAddAgent(run: AnalysisRunRef) {
  const used = form.value.runs.filter(r => r.execution_id === run.execution_id).length
  return used < agentsOf(run.execution_id).length
}

function addAgentRun(index: number) {
  const run = form.value.runs[index]!
  const taken = new Set(form.value.runs.filter(r => r.execution_id === run.execution_id).map(r => r.agent_name))
  const next = agentsOf(run.execution_id).find(a => !taken.has(a.name))
  if (next)
    form.value.runs.splice(index + 1, 0, { execution_id: run.execution_id, agent_name: next.name, label: null })
}

// --- Prediction path: suggestions from the outputs, or any path typed in ---

const pathOpen = ref(false)
const customPaths = ref<string[]>([])

// A combobox item can't have an empty value, so the whole output gets a stand-in
const WHOLE_OUTPUT = '__whole_output__'

const pathModel = computed({
  get: () => form.value.config.output_path || WHOLE_OUTPUT,
  set: (value: string) => {
    form.value.config.output_path = value === WHOLE_OUTPUT ? '' : value
  },
})

const pathItems = computed(() => {
  const paths = new Set([...pathSuggestions.value, ...customPaths.value])
  if (form.value.config.output_path)
    paths.add(form.value.config.output_path)
  return [
    { label: '(whole output)', value: WHOLE_OUTPUT },
    ...[...paths].map(p => ({ label: p, value: p })),
  ]
})

function createPath(path: string) {
  const trimmed = path.trim()
  if (!trimmed)
    return
  customPaths.value.push(trimmed)
  form.value.config.output_path = trimmed
  pathOpen.value = false
}

// --- Values and metrics ---

const valueTypeItems: { label: string, value: AnalysisValueType, hint: string }[] = [
  { label: 'Numeric', value: 'numeric', hint: 'Scores, ratings, any number' },
  { label: 'Categorical', value: 'categorical', hint: 'Labels, classes, yes/no' },
]

const kindMetrics = computed(() => (metrics.value ?? []).filter(m => m.kind === form.value.config.value_type))

function toggleMetric(key: string) {
  const selected = form.value.config.metrics
  form.value.config.metrics = selected.includes(key) ? selected.filter(k => k !== key) : [...selected, key]
}

// Switching kind selects every metric of the new kind
watch(() => form.value.config.value_type, (kind: AnalysisValueType, previous) => {
  if (previous && kind !== previous)
    form.value.config.metrics = (metrics.value ?? []).filter(m => m.kind === kind).map(m => m.key)
})

const confidenceItems = [
  { label: '90%', value: 0.9 },
  { label: '95%', value: 0.95 },
  { label: '99%', value: 0.99 },
]
</script>

<template>
  <div class="space-y-8">
    <!-- The title is the form's heading: no label, no box -->
    <div class="space-y-1">
      <input
        ref="nameInput"
        v-model="form.name"
        type="text"
        aria-label="Name"
        placeholder="Analysis name"
        autocomplete="off"
        class="w-full bg-transparent text-xl font-semibold text-highlighted outline-none placeholder:text-dimmed"
      >
      <input
        :value="form.description ?? ''"
        type="text"
        aria-label="Description"
        placeholder="Add a description…"
        autocomplete="off"
        class="w-full bg-transparent text-sm text-toned outline-none placeholder:text-dimmed"
        @input="form.description = ($event.target as HTMLInputElement).value || null"
      >
      <TagsInput v-model="form.tag_ids" class="pt-1.5" />
    </div>

    <section class="space-y-2" aria-labelledby="analysis-executions">
      <div class="flex items-center justify-between gap-3">
        <div class="min-w-0">
          <h2 id="analysis-executions" class="text-sm font-medium text-highlighted">
            Executions
            <span v-if="form.runs.length" class="ml-1 font-normal text-muted tabular-nums">{{ form.runs.length }}</span>
          </h2>
          <p class="text-xs text-muted">
            Each one is compared to the ground truth on its own.
          </p>
        </div>

        <USelectMenu
          v-model="pickedExecutions"
          multiple
          :items="executionItems"
          value-key="value"
          :search-input="{ placeholder: 'Search executions…' }"
          :content="{ align: 'end' }"
          :trailing-icon="false"
          :ui="{ content: 'min-w-[28rem]' }"
          variant="ghost"
          color="neutral"
          size="sm"
          class="w-auto shrink-0"
        >
          <span class="flex items-center gap-1.5">
            <UIcon name="i-ph-plus-bold" class="size-4 shrink-0" aria-hidden="true" />
            Add execution
          </span>
          <template #item-trailing="{ item }">
            <UIRowCount :rows="item.rows" size="xs" class="text-xs text-muted" />
          </template>
        </USelectMenu>
      </div>

      <ul v-if="form.runs.length" ref="runList" class="divide-y divide-default rounded-lg border border-default">
        <li
          v-for="(run, index) in form.runs"
          :key="runKey(run)"
          class="group flex items-start gap-2 px-2 py-2.5"
        >
          <button
            type="button"
            :data-drag-handle="runKey(run)"
            aria-label="Reorder: drag, or use the up and down arrow keys"
            class="mt-0.5 flex size-5 shrink-0 cursor-grab items-center justify-center rounded text-dimmed opacity-0 outline-none transition-opacity duration-150 hover:text-toned focus-visible:opacity-100 focus-visible:outline-2 focus-visible:outline-inverted group-hover:opacity-100 active:cursor-grabbing"
            @keydown.up.prevent="moveRun(run, -1)"
            @keydown.down.prevent="moveRun(run, 1)"
          >
            <UIcon name="i-ph-dots-six-vertical-bold" class="size-4" aria-hidden="true" />
          </button>

          <span
            class="mt-0.5 shrink-0 rounded bg-elevated px-1.5 py-0.5 font-mono text-xs text-toned tabular-nums"
            :title="`Execution ${run.execution_id}`"
          >
            #{{ run.execution_id }}
          </span>

          <div class="min-w-0 flex-1 space-y-1">
            <input
              v-if="renaming === index"
              v-focus
              :value="run.label ?? ''"
              type="text"
              aria-label="Name in this comparison"
              :placeholder="executionOf(run.execution_id)?.experiment_name"
              autocomplete="off"
              class="w-full rounded bg-elevated px-1.5 py-0.5 -my-0.5 text-sm text-highlighted outline-none ring-1 ring-inverted"
              @input="run.label = ($event.target as HTMLInputElement).value || null"
              @keydown.enter.prevent="renaming = null"
              @keydown.esc.prevent="stopRenaming(run)"
              @blur="renaming = null"
            >
            <p v-else class="truncate text-sm text-highlighted" :title="run.label ?? executionOf(run.execution_id)?.experiment_name">
              {{ run.label || executionOf(run.execution_id)?.experiment_name || `Execution ${run.execution_id}` }}
            </p>

            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
              <UIMetaItem v-if="executionOf(run.execution_id)?.dataset_name" icon="i-ph-database-bold" label="Dataset">
                <span class="truncate">{{ executionOf(run.execution_id)!.dataset_name }}</span>
              </UIMetaItem>
              <UIMetaItem v-if="executionOf(run.execution_id)" icon="i-ph-calendar-blank-bold" label="Started">
                {{ formatShortDate(executionOf(run.execution_id)!.started_at) }}
              </UIMetaItem>
              <UIMetaItem v-if="executionOf(run.execution_id)" icon="i-ph-rows-bold" label="Rows">
                <UIRowCount :rows="executionOf(run.execution_id)!.row_count" size="xs" class="text-xs" />
              </UIMetaItem>
              <template v-if="agentsOf(run.execution_id).length <= 1">
                <UIMetaItem v-if="run.agent_name" icon="i-ph-ghost-bold" label="Agent">
                  <span class="truncate">{{ run.agent_name }}</span>
                </UIMetaItem>
                <UIMetaItem v-if="modelOf(run)" icon="i-ph-cpu-bold" label="Model">
                  <span class="truncate">{{ modelOf(run) }}</span>
                </UIMetaItem>
              </template>
            </div>
          </div>

          <!-- Several agents: the one whose output holds the prediction -->
          <USelect
            v-if="agentsOf(run.execution_id).length > 1"
            v-model="run.agent_name"
            :items="agentItems(run.execution_id)"
            icon="i-ph-ghost-bold"
            variant="subtle"
            color="neutral"
            size="xs"
            aria-label="Agent whose output holds the prediction"
            class="w-52 shrink-0"
          />

          <div class="flex shrink-0 items-center opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100">
            <UTooltip text="Rename in this comparison">
              <UButton
                icon="i-ph-pencil-simple-bold"
                variant="ghost"
                color="neutral"
                size="xs"
                aria-label="Rename in this comparison"
                @mousedown.prevent
                @click="() => { renaming = index }"
              />
            </UTooltip>
            <UTooltip v-if="canAddAgent(run)" text="Compare another agent">
              <UButton
                icon="i-ph-copy-bold"
                variant="ghost"
                color="neutral"
                size="xs"
                aria-label="Compare another agent of this execution"
                @click="addAgentRun(index)"
              />
            </UTooltip>
            <UButton
              icon="i-ph-x-bold"
              variant="ghost"
              color="neutral"
              size="xs"
              aria-label="Remove"
              @click="removeRun(index)"
            />
          </div>
        </li>
      </ul>
      <p v-else class="rounded-lg border border-dashed border-default px-4 py-6 text-center text-sm text-muted">
        Add the executions you want to compare.
      </p>
    </section>

    <section class="space-y-2" aria-labelledby="analysis-comparison">
      <h2 id="analysis-comparison" class="text-sm font-medium text-highlighted">
        Comparison
      </h2>

      <div class="divide-y divide-default rounded-lg border border-default">
        <AnalysesField label="Ground truth" hint="Dataset column with the expected value" required>
          <USelectMenu
            v-model="form.config.truth_column"
            :items="columns"
            :placeholder="form.runs.length ? 'Select a column' : 'Add an execution first'"
            :disabled="!form.runs.length"
            :ui="{ value: 'font-mono text-xs' }"
            size="sm"
            class="w-64"
          />
        </AnalysesField>

        <AnalysesField label="Prediction" hint="Path in the agent's JSON output, like evaluation.score">
          <USelectMenu
            v-model="pathModel"
            v-model:open="pathOpen"
            :items="pathItems"
            value-key="value"
            create-item="always"
            :search-input="{ placeholder: 'Search or type a path…' }"
            :ui="{ value: 'font-mono text-xs' }"
            size="sm"
            class="w-64"
            @create="createPath"
          >
            <template #create-item-label="{ item }">
              Use <span class="font-mono text-xs">{{ item }}</span>
            </template>
          </USelectMenu>
        </AnalysesField>

        <AnalysesField label="Values">
          <UFieldGroup>
            <UButton
              v-for="type in valueTypeItems"
              :key="type.value"
              :label="type.label"
              :title="type.hint"
              :variant="form.config.value_type === type.value ? 'subtle' : 'outline'"
              color="neutral"
              size="sm"
              :aria-pressed="form.config.value_type === type.value"
              @click="() => { form.config.value_type = type.value }"
            />
          </UFieldGroup>
        </AnalysesField>

        <AnalysesField label="Metrics" required>
          <UTooltip v-for="metric in kindMetrics" :key="metric.key" :text="metric.description">
            <UButton
              :label="metric.label"
              :icon="form.config.metrics.includes(metric.key) ? 'i-ph-check-bold' : undefined"
              :variant="form.config.metrics.includes(metric.key) ? 'subtle' : 'outline'"
              color="neutral"
              size="xs"
              :aria-pressed="form.config.metrics.includes(metric.key)"
              @click="toggleMetric(metric.key)"
            />
          </UTooltip>
        </AnalysesField>

        <AnalysesField v-if="form.config.value_type === 'categorical'" label="Ignore case" hint="Treat “Yes” and “yes” as the same label">
          <USwitch v-model="form.config.ignore_case" aria-label="Ignore case" />
        </AnalysesField>

        <UCollapsible>
          <template #default="{ open }">
            <UButton
              variant="ghost"
              color="neutral"
              size="sm"
              block
              class="justify-between rounded-none px-4 py-2.5 text-muted active:scale-100!"
              :trailing-icon="open ? 'i-ph-caret-up-bold' : 'i-ph-caret-down-bold'"
            >
              Confidence intervals
            </UButton>
          </template>
          <template #content>
            <div class="divide-y divide-default border-t border-default">
              <AnalysesField label="Bootstrap resamples" hint="0 turns the intervals off">
                <UInputNumber v-model="form.config.n_boot" :min="0" :max="10000" :step="100" size="sm" class="w-32" />
              </AnalysesField>
              <AnalysesField label="Confidence level">
                <USelect v-model="form.config.confidence" :items="confidenceItems" size="sm" class="w-32" />
              </AnalysesField>
              <AnalysesField label="Seed" hint="Same seed, same intervals">
                <UInputNumber v-model="form.config.seed" :min="0" size="sm" class="w-32" />
              </AnalysesField>
            </div>
          </template>
        </UCollapsible>
      </div>
    </section>
  </div>
</template>
