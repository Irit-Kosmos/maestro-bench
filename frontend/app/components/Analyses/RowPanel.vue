<script setup lang="ts">
import type { AnalysisRunResult, ExecutionRow } from '~/types'
import { cellText } from '~/composables/useDatasetEditor'

// One point of an analysis in full: the dataset row it comes from and what
// every agent returned for it, to understand why a prediction is off.
const props = defineProps<{
  run: AnalysisRunResult | null
  rowIndex: number | null
  truthColumn: string
}>()

const open = defineModel<boolean>('open', { default: false })

const { fetchExecutionRow } = useAnalyses()

const row = ref<ExecutionRow | null>(null)
const loading = ref(false)
const error = ref<string | null>(null)

const point = computed(() =>
  props.run?.points?.find(p => p.row_index === props.rowIndex) ?? null,
)

// Latest request wins when the user clicks through points quickly
let request = 0
watch(
  () => [open.value, props.run?.execution_id, props.rowIndex] as const,
  async ([isOpen, executionId, rowIndex]) => {
    if (!isOpen || executionId === undefined || rowIndex === null)
      return
    const current = ++request
    row.value = null
    error.value = null
    loading.value = true
    try {
      const data = await fetchExecutionRow(executionId, rowIndex)
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
        icon="i-lucide-circle-x"
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
          icon="i-lucide-circle-x"
          :title="row.error"
        />

        <section class="flex flex-col gap-3">
          <h4 class="text-sm font-semibold text-highlighted">
            Dataset row
          </h4>
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
          <h4 class="text-sm font-semibold text-highlighted">
            Agent outputs
          </h4>
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
            <UAlert
              v-if="agent.error"
              color="error"
              variant="subtle"
              icon="i-lucide-circle-x"
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
  </USlideover>
</template>
