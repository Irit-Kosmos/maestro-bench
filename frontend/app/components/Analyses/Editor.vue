<script setup lang="ts">
import type { AnalysisForm, AnalysisValueType, AvailableExecution, ExecutionFields, MetricInfo } from '~/types'

const form = defineModel<AnalysisForm>({ required: true })

const { fetchExecutionFields } = useAnalyses()
const { formatDate } = useUIHelpers()

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

const executionItems = computed(() => (executions.value ?? []).map(e => ({
  label: `#${e.execution_id} · ${e.experiment_name}`,
  description: [e.dataset_name, e.agents.map(a => a.model).join(', '), formatDate(e.started_at)]
    .filter(Boolean)
    .join(' · '),
  value: e.execution_id,
  rows: e.row_count,
})))

function rowsOf(executionId: number) {
  return executions.value?.find(e => e.execution_id === executionId)?.row_count ?? null
}

function agentItems(executionId: number) {
  return (fields.value[executionId]?.agents ?? []).map(a => ({
    label: a.model ? `${a.name} (${a.model})` : a.name,
    value: a.name,
  }))
}

function defaultLabel(executionId: number, agentName: string) {
  const execution = executions.value?.find(e => e.execution_id === executionId)
  const model = fields.value[executionId]?.agents.find(a => a.name === agentName)?.model
  return [execution?.experiment_name, model].filter(Boolean).join(' · ')
}

const addExecution = ref<number | undefined>()
watch(addExecution, (id) => {
  if (id === undefined)
    return
  form.value.runs.push({ execution_id: id, agent_name: '', label: null })
  addExecution.value = undefined
})

function removeRun(index: number) {
  form.value.runs.splice(index, 1)
}

// The order of the runs is the order of the comparison
function moveRun(index: number, offset: -1 | 1) {
  const runs = form.value.runs
  const target = index + offset
  if (target < 0 || target >= runs.length)
    return
  const [run] = runs.splice(index, 1)
  runs.splice(target, 0, run!)
}

const valueTypeItems = [
  { label: 'Numeric', value: 'numeric', description: 'Scores, ratings, any number' },
  { label: 'Categorical', value: 'categorical', description: 'Labels, classes, yes/no' },
]

const metricItems = computed(() => (metrics.value ?? [])
  .filter(m => m.kind === form.value.config.value_type)
  .map(m => ({ label: m.label, value: m.key, description: m.description })))

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
  <div class="space-y-6">
    <div class="grid gap-4 md:grid-cols-2">
      <UFormField label="Name" required>
        <UInput v-model="form.name" placeholder="e.g. Mohler graders" class="w-full" />
      </UFormField>
      <UFormField label="Description">
        <UInput
          :model-value="form.description ?? ''"
          placeholder="Optional"
          class="w-full"
          @update:model-value="(v: string) => form.description = v || null"
        />
      </UFormField>
    </div>

    <section class="space-y-3">
      <div>
        <h3 class="font-semibold">
          Executions
        </h3>
        <p class="text-sm text-muted">
          Each execution is compared to the ground truth independently; pick the agent whose output holds the prediction.
        </p>
      </div>

      <div
        v-for="(run, index) in form.runs"
        :key="index"
        class="space-y-3 p-3 rounded-md border border-default"
      >
        <div class="flex items-end gap-2">
          <UFormField label="Execution" class="flex-1 min-w-0">
            <template #hint>
              <UIRowCount :rows="rowsOf(run.execution_id)" size="xs" class="text-xs text-muted" />
            </template>
            <USelectMenu
              v-model="run.execution_id"
              :items="executionItems"
              value-key="value"
              class="w-full"
              @update:model-value="run.agent_name = ''"
            >
              <template #item-trailing="{ item }">
                <UIRowCount :rows="item.rows" size="xs" class="text-xs text-muted" />
              </template>
            </USelectMenu>
          </UFormField>
          <div class="flex items-center shrink-0">
            <UButton
              icon="i-lucide-chevron-up"
              variant="ghost"
              color="neutral"
              size="sm"
              aria-label="Move execution up"
              :disabled="index === 0"
              @click="moveRun(index, -1)"
            />
            <UButton
              icon="i-lucide-chevron-down"
              variant="ghost"
              color="neutral"
              size="sm"
              aria-label="Move execution down"
              :disabled="index === form.runs.length - 1"
              @click="moveRun(index, 1)"
            />
            <UButton
              icon="i-lucide-x"
              variant="ghost"
              color="neutral"
              size="sm"
              aria-label="Remove execution"
              @click="removeRun(index)"
            />
          </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
          <UFormField label="Agent" class="min-w-0">
            <USelect
              v-model="run.agent_name"
              :items="agentItems(run.execution_id)"
              placeholder="Loading agents…"
              class="w-full"
            />
          </UFormField>
          <UFormField label="Label" class="min-w-0">
            <UInput
              :model-value="run.label ?? ''"
              :placeholder="defaultLabel(run.execution_id, run.agent_name)"
              class="w-full"
              @update:model-value="(v: string) => run.label = v || null"
            />
          </UFormField>
        </div>
      </div>

      <USelectMenu
        v-model="addExecution"
        :items="executionItems"
        value-key="value"
        placeholder="Add an execution…"
        icon="i-lucide-plus"
        class="w-full md:w-96"
      >
        <template #item-trailing="{ item }">
          <UIRowCount :rows="item.rows" size="xs" class="text-xs text-muted" />
        </template>
      </USelectMenu>
    </section>

    <section class="space-y-3">
      <h3 class="font-semibold">
        Prediction and ground truth
      </h3>
      <div class="grid gap-4 md:grid-cols-2">
        <UFormField label="Ground truth column" required help="Dataset column the predictions are compared to">
          <USelect
            v-model="form.config.truth_column"
            :items="columns"
            :placeholder="form.runs.length ? 'Select a column' : 'Add an execution first'"
            class="w-full"
          />
        </UFormField>
        <UFormField label="Output path" help="Dotted path in the agent's JSON output (e.g. score, evaluation.score). Empty = whole output.">
          <UInput v-model="form.config.output_path" placeholder="(whole output)" class="w-full" />
          <div v-if="pathSuggestions.length" class="flex flex-wrap gap-1 mt-2">
            <UButton
              v-for="path in pathSuggestions"
              :key="path"
              size="xs"
              :variant="form.config.output_path === path ? 'solid' : 'soft'"
              color="neutral"
              @click="() => { form.config.output_path = path }"
            >
              {{ path || '(whole output)' }}
            </UButton>
          </div>
        </UFormField>
      </div>

      <UFormField label="Value type">
        <URadioGroup
          v-model="form.config.value_type"
          :items="valueTypeItems"
          orientation="horizontal"
          variant="card"
        />
      </UFormField>

      <UFormField label="Metrics" required>
        <UCheckboxGroup
          v-model="form.config.metrics"
          :items="metricItems"
          orientation="horizontal"
        />
      </UFormField>

      <UCheckbox
        v-if="form.config.value_type === 'categorical'"
        v-model="form.config.ignore_case"
        label="Ignore case when comparing labels"
      />
    </section>

    <UCollapsible>
      <UButton
        variant="link"
        color="neutral"
        trailing-icon="i-lucide-chevron-down"
        class="px-0"
      >
        Advanced
      </UButton>
      <template #content>
        <div class="grid gap-4 md:grid-cols-3 pt-2">
          <UFormField label="Bootstrap resamples" help="0 disables confidence intervals">
            <UInputNumber v-model="form.config.n_boot" :min="0" :max="10000" :step="100" class="w-full" />
          </UFormField>
          <UFormField label="Confidence level">
            <USelect v-model="form.config.confidence" :items="confidenceItems" class="w-full" />
          </UFormField>
          <UFormField label="Seed" help="Same seed, same intervals">
            <UInputNumber v-model="form.config.seed" :min="0" class="w-full" />
          </UFormField>
        </div>
      </template>
    </UCollapsible>
  </div>
</template>
