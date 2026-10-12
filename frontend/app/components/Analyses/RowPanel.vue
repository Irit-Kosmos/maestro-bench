<script setup lang="ts">
import type { AnalysisRunResult, ExecutionRow } from '~/types'
import { cellText } from '~/composables/useDatasetEditor'

// One point of an analysis in full: the dataset row it comes from and what
// every agent returned for it, to understand why a prediction is off.
const props = defineProps<{
  run: AnalysisRunResult | null
  /** Rows sharing the clicked point; the panel steps through them */
  rows: number[]
  /** Position of the shown row among `rows` */
  index: number
  truthColumn: string
}>()

const emit = defineEmits<{
  navigate: [delta: number]
}>()

const open = defineModel<boolean>('open', { default: false })

const { fetchExecutionRow } = useAnalyses()

const row = ref<ExecutionRow | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const rowIndex = computed(() => props.rows[props.index] ?? null)

// Numeric runs list their points; categorical ones know a row through its confusion cell
const point = computed<{ pred: number | string, truth: number | string } | null>(() => {
  const { confusion, points } = props.run ?? {}
  const found = points?.find(p => p.row_index === rowIndex.value)
  if (found)
    return found
  if (!confusion?.rows)
    return null
  for (const [i, cells] of confusion.rows.entries()) {
    const j = cells.findIndex(rows => rows.includes(rowIndex.value as number))
    if (j >= 0)
      return { truth: confusion.labels[i]!, pred: confusion.labels[j]! }
  }
  return null
})

// Latest request wins when the user clicks through points quickly
let request = 0
watch(
  () => [open.value, props.run?.execution_id, rowIndex.value] as const,
  async ([isOpen, executionId, selectedRow]) => {
    if (!isOpen || executionId === undefined || selectedRow === null)
      return
    const current = ++request
    row.value = null
    error.value = null
    loading.value = true
    try {
      const data = await fetchExecutionRow(executionId, selectedRow)
      if (current === request)
        row.value = data
    }
    catch (e) {
      if (current === request)
        error.value = apiErrorMessage(e) ?? 'Couldn’t load this row.'
    }
    finally {
      if (current === request)
        loading.value = false
    }
  },
  { immediate: true },
)

// What an aggregator computed from: "langue = 3 · contenu = 4"
function inputsText(inputs: Record<string, unknown> | null | undefined): string {
  return Object.entries(inputs ?? {}).map(([k, v]) => `${k} = ${formatFormulaValue(v)}`).join(' · ')
}

// Typing in a field is left alone: these only fire outside inputs
defineShortcuts({
  j: () => open.value && emit('navigate', 1),
  k: () => open.value && emit('navigate', -1),
})

function outputText(output: unknown): string {
  if (typeof output === 'string')
    return output
  return output === null || output === undefined ? '' : JSON.stringify(output, null, 2)
}
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="`Row ${rowIndex ?? ''}`"
    :description="run ? `${run.label} · ${run.agent_name}` : undefined"
    :ui="{ content: 'max-w-xl' }"
  >
    <template #body>
      <BaseLoadingState v-if="loading" size="sm" />
      <UAlert
        v-else-if="error"
        color="error"
        variant="subtle"
        icon="i-ph-x-circle-bold"
        :title="error"
      />
      <div v-else-if="row" class="flex flex-col gap-6">
        <dl v-if="point" class="grid grid-cols-2 gap-3 text-sm">
          <div class="rounded-md border border-default px-3 py-2">
            <dt class="text-xs text-muted">
              Predicted
            </dt>
            <dd class="font-medium tabular-nums text-highlighted">
              {{ point.pred }}
            </dd>
          </div>
          <div class="rounded-md border border-default px-3 py-2">
            <dt class="text-xs text-muted">
              Ground truth
            </dt>
            <dd class="font-medium tabular-nums text-highlighted">
              {{ point.truth }}
            </dd>
          </div>
        </dl>

        <UAlert
          v-if="row.error"
          color="error"
          variant="subtle"
          icon="i-ph-x-circle-bold"
          :title="row.error"
        />

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">
            Dataset row
          </h3>
          <div v-for="(value, key) in row.input_data" :key="key">
            <label
              :for="`analysis-row-${key}`"
              class="flex items-center gap-2 mb-1 text-xs font-medium font-mono text-muted"
            >
              {{ key }}
              <UBadge
                v-if="key === truthColumn"
                label="ground truth"
                color="primary"
                variant="soft"
                size="sm"
                class="font-sans"
              />
            </label>
            <UTextarea
              :id="`analysis-row-${key}`"
              :model-value="cellText(value)"
              readonly
              autoresize
              :rows="1"
              :maxrows="14"
              class="w-full"
              :ui="{ base: 'text-muted' }"
            />
          </div>
        </section>

        <section class="flex flex-col gap-3">
          <h3 class="text-sm font-semibold text-highlighted">
            Agent outputs
          </h3>
          <div v-for="(agent, i) in row.agents" :key="`${agent.name}-${i}`">
            <label
              :for="`analysis-agent-${i}`"
              class="flex items-center gap-2 mb-1 text-xs font-medium font-mono text-muted"
            >
              {{ agent.name }}
              <UBadge
                v-if="agent.name === run?.agent_name"
                label="analysed"
                color="primary"
                variant="soft"
                size="sm"
                class="font-sans"
              />
            </label>
            <p
              v-if="agent.kind === 'aggregator' && inputsText(agent.inputs)"
              class="mb-1 flex items-center gap-1.5 font-mono text-xs text-toned"
            >
              <UIcon name="i-ph-function-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
              <span class="min-w-0">{{ inputsText(agent.inputs) }}</span>
            </p>
            <UAlert
              v-if="agent.error"
              color="error"
              variant="subtle"
              icon="i-ph-x-circle-bold"
              :title="agent.error"
            />
            <UTextarea
              v-else
              :id="`analysis-agent-${i}`"
              :model-value="outputText(agent.output)"
              readonly
              autoresize
              :rows="1"
              :maxrows="14"
              class="w-full"
              :ui="{ base: 'text-muted font-mono' }"
            />
          </div>
          <p v-if="!row.agents.length" class="text-sm text-muted">
            No agent ran on this row.
          </p>
        </section>
      </div>
    </template>

    <template v-if="rows.length > 1" #footer>
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-1">
          <UTooltip text="Previous row" :kbds="['k']">
            <UButton
              icon="i-ph-caret-up-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Previous row"
              :disabled="index <= 0"
              @click="emit('navigate', -1)"
            />
          </UTooltip>
          <UTooltip text="Next row" :kbds="['j']">
            <UButton
              icon="i-ph-caret-down-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Next row"
              :disabled="index >= rows.length - 1"
              @click="emit('navigate', 1)"
            />
          </UTooltip>
        </div>
        <span class="text-sm text-muted tabular-nums">
          {{ index + 1 }} of {{ rows.length }} rows on this point
        </span>
      </div>
    </template>
  </USlideover>
</template>
