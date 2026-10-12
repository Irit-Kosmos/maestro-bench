<script setup lang="ts">
import type { Agent, AgentConfiguration, AgentInputMapping, FormulaOutput } from '~/types'

// The settings of an aggregator in an experiment: its outputs, each computed by a formula, and where
// each variable of the formulas gets its value. Formulas run in order: a later one can read an earlier one.
const props = defineProps<{
  config: AgentConfiguration | undefined
  datasetHeaders: readonly string[]
  /** Agents whose output this aggregator may read, nearest last */
  upstreamAgents: readonly Agent[]
  /** Smaller type, for a side panel */
  compact?: boolean
}>()

const emit = defineEmits<{
  update: [field: 'formulas', value: FormulaOutput[]]
  setMapping: [mapping: AgentInputMapping]
}>()

const ids = useId()

const formulas = computed(() => props.config?.formulas ?? [])
const variables = computed(() => formulaVariables(formulas.value))

const { check, preview, previewing, runPreview } = useFormulaCheck(
  computed(() => props.config?.formulas),
  computed(() => props.config?.input_mappings),
)

function errorOf(index: number) {
  return check.value?.errors[index] ?? null
}

function nameInvalid(index: number) {
  return !!errorOf(index) && !!check.value?.name_invalid?.[index]
}

function patch(index: number, change: Partial<FormulaOutput>) {
  emit('update', 'formulas', formulas.value.map((f, i) => i === index ? { ...f, ...change } : f))
}

const formulaInputs = useTemplateRef<{ inputRef: HTMLInputElement }[]>('formulaInputs')

async function addOutput() {
  const taken = new Set(formulas.value.map(f => f.name))
  let n = formulas.value.length + 1
  while (taken.has(`output_${n}`))
    n++
  emit('update', 'formulas', [...formulas.value, { name: `output_${n}`, formula: '' }])
  await nextTick()
  formulaInputs.value?.at(-1)?.inputRef?.focus()
}

function removeOutput(index: number) {
  emit('update', 'formulas', formulas.value.filter((_, i) => i !== index))
}

const canPreview = computed(() => (props.config?.input_mappings ?? [])
  .some(m => m.source === 'agent' && m.sourceAgentId !== undefined && variables.value.includes(m.variable)))

// A preview answers the formulas it was run with: editing them makes it stale
watch(() => [props.config?.formulas, props.config?.input_mappings], () => {
  preview.value = null
}, { deep: true })

function inputsLabel(inputs: Record<string, unknown>) {
  return Object.entries(inputs).map(([k, v]) => `${k} = ${formatFormulaValue(v)}`).join(' · ')
}

function outputLabel(output: Record<string, unknown>) {
  return Object.entries(output).map(([k, v]) => `${k} = ${formatFormulaValue(v)}`).join(' · ')
}
</script>

<template>
  <div class="@container flex flex-col" :class="compact ? 'gap-4' : 'gap-5'">
    <!-- Outputs -->
    <section :aria-labelledby="`${ids}-outputs`">
      <div class="flex items-baseline justify-between gap-2">
        <h4 :id="`${ids}-outputs`" class="font-medium text-highlighted" :class="compact ? 'text-xs' : 'text-sm'">
          Outputs
        </h4>
        <UPopover :content="{ align: 'end' }">
          <UButton variant="link" color="neutral" size="xs" icon="i-ph-function-bold" class="-my-1">
            Functions
          </UButton>
          <template #content>
            <div class="max-w-80 p-3">
              <p class="text-xs text-muted">
                Formulas use <code class="font-mono">+ - * / // % **</code>, comparisons,
                <code class="font-mono">and or not</code> and <code class="font-mono">a if condition else b</code>.
              </p>
              <dl class="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
                <template v-for="fn in FORMULA_FUNCTIONS" :key="fn.name">
                  <dt class="font-mono text-highlighted">
                    {{ fn.signature }}
                  </dt>
                  <dd class="text-muted">
                    {{ fn.description }}
                  </dd>
                </template>
              </dl>
            </div>
          </template>
        </UPopover>
      </div>
      <p class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
        Computed in order on every row, a later formula can use an earlier output. An analysis compares any of them to the ground truth.
      </p>

      <ul class="mt-3 flex flex-col gap-2">
        <li v-for="(output, index) in formulas" :key="index">
          <div class="flex items-center gap-2">
            <UInput
              :model-value="output.name"
              placeholder="name"
              size="sm"
              class="shrink-0" :class="compact ? 'w-24' : 'w-32'"
              :ui="{ base: 'font-mono text-xs' }"
              :color="nameInvalid(index) ? 'error' : 'neutral'"
              :highlight="nameInvalid(index)"
              :aria-label="`Name of output ${index + 1}`"
              :aria-invalid="nameInvalid(index)"
              :aria-describedby="nameInvalid(index) ? `${ids}-error-${index}` : undefined"
              @update:model-value="(value: string | number) => patch(index, { name: String(value).trim() })"
            />
            <span class="text-sm text-dimmed" aria-hidden="true">=</span>
            <UInput
              ref="formulaInputs"
              :model-value="output.formula"
              placeholder="0.4 * language + 0.6 * content"
              size="sm"
              class="min-w-0 flex-1"
              :ui="{ base: 'font-mono text-xs' }"
              :color="errorOf(index) && !nameInvalid(index) ? 'error' : 'neutral'"
              :highlight="!!errorOf(index) && !nameInvalid(index)"
              :aria-label="`Formula of ${output.name || `output ${index + 1}`}`"
              :aria-invalid="!!errorOf(index) && !nameInvalid(index)"
              :aria-describedby="errorOf(index) && !nameInvalid(index) ? `${ids}-error-${index}` : undefined"
              @update:model-value="(value: string | number) => patch(index, { formula: String(value) })"
            />
            <UButton
              v-if="formulas.length > 1"
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-ph-x-bold"
              :aria-label="`Remove ${output.name || `output ${index + 1}`}`"
              @click="removeOutput(index)"
            />
          </div>
          <p v-if="errorOf(index)" :id="`${ids}-error-${index}`" class="mt-1 text-xs text-error" :class="nameInvalid(index) ? '' : compact ? 'ps-26' : 'ps-34'">
            {{ errorOf(index) }}
          </p>
        </li>
      </ul>

      <UButton class="mt-2" color="neutral" variant="ghost" size="sm" icon="i-ph-plus-bold" @click="addOutput">
        Add output
      </UButton>
    </section>

    <ExperimentsVariableMappings
      :variables="variables"
      :mappings="config?.input_mappings"
      :dataset-headers="datasetHeaders"
      :upstream-agents="upstreamAgents"
      title="Formula variables"
      description="Where each variable gets its value for every row. Weights are fixed values, so they stay out of the formula."
      static-label="Fixed value"
      static-placeholder="A number or a text, like 0.4"
      :is-complete="isFormulaMappingComplete"
      with-lists
      :compact="compact"
      @set-mapping="mapping => emit('setMapping', mapping)"
    />

    <!-- Preview on what agents already returned -->
    <section v-if="variables.length > 0" :aria-labelledby="`${ids}-preview`">
      <div class="flex items-center justify-between gap-2">
        <h4 :id="`${ids}-preview`" class="font-medium text-highlighted" :class="compact ? 'text-xs' : 'text-sm'">
          Preview
        </h4>
        <UButton
          color="neutral"
          variant="outline"
          size="xs"
          icon="i-ph-play-bold"
          :loading="previewing"
          :disabled="!canPreview"
          @click="runPreview"
        >
          Try on a past run
        </UButton>
      </div>
      <p v-if="!preview" class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
        {{ canPreview
          ? 'Computes the outputs on the first rows of the latest run of the agents they read.'
          : 'Map a variable to a previous agent to try the formulas on what it returned.' }}
      </p>
      <p v-else-if="preview.execution_id === null" class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
        No completed run has every agent these formulas read yet.
      </p>
      <template v-else>
        <p class="mt-0.5 text-muted" :class="compact ? 'text-xs' : 'text-sm'">
          First rows of execution #{{ preview.execution_id }}<template v-if="preview.experiment_name">
            ({{ preview.experiment_name }})
          </template>
        </p>
        <p v-if="!preview.versions_match" class="mt-1 flex items-center gap-1.5 text-xs text-warning">
          <UIcon name="i-ph-warning-bold" class="size-3.5 shrink-0" aria-hidden="true" />
          No run used the prompt versions set here: these rows come from other versions, which may answer differently.
        </p>
        <ul class="mt-2 divide-y divide-default rounded-lg border border-default text-xs">
          <li v-for="row in preview.rows" :key="row.row_index ?? undefined" class="flex flex-col gap-0.5 px-3 py-2">
            <span class="flex items-baseline gap-2">
              <span class="shrink-0 text-muted tabular-nums">#{{ row.row_index }}</span>
              <span v-if="row.output" class="font-mono text-highlighted">{{ outputLabel(row.output) }}</span>
              <span v-else class="text-error">{{ row.error }}</span>
            </span>
            <span v-if="Object.keys(row.inputs).length" class="truncate ps-6 font-mono text-muted" :title="inputsLabel(row.inputs)">
              {{ inputsLabel(row.inputs) }}
            </span>
          </li>
        </ul>
      </template>
    </section>
  </div>
</template>
