<script setup lang="ts">
import type { AnalysisConfig, AnalysisResult, AnalysisRunResult, MetricInfo } from '~/types'
import { EXCLUSION_LABELS } from '~/composables/useAnalyses'

const props = defineProps<{
  result: AnalysisResult
  config: AnalysisConfig
  name?: string
}>()

const okRuns = computed(() => props.result.runs.filter(r => r.status === 'ok'))
const failedRuns = computed(() => props.result.runs.filter(r => r.status !== 'ok'))
const confidencePct = computed(() => Math.round(props.config.confidence * 100))

// One shared domain for the predicted-vs-actual plots
const scatterDomain = computed<[number, number]>(() => {
  const values = okRuns.value.flatMap(r => (r.points ?? []).flatMap(p => [p.pred, p.truth]))
  if (!values.length)
    return [0, 1]
  return [Math.min(...values) - 0.5, Math.max(...values) + 0.5]
})

// Rows shown in the side panel after a click on a point: several when they share its position
const selected = ref<{ run: AnalysisRunResult, rows: number[], index: number } | null>(null)
const panelOpen = ref(false)

function selectPoint(run: AnalysisRunResult, rows: number[]) {
  selected.value = { run, rows, index: 0 }
  panelOpen.value = true
}

function selectedRowOf(run: AnalysisRunResult) {
  const current = selected.value
  return current && current.run.execution_id === run.execution_id
    && current.run.agent_name === run.agent_name
    ? current.rows[current.index] ?? null
    : null
}

function navigate(delta: number) {
  const current = selected.value
  if (!current)
    return
  const index = current.index + delta
  if (index >= 0 && index < current.rows.length)
    current.index = index
}

// Default labels read "Experiment · model"; the model id goes on the secondary line
function splitLabel(label: string) {
  const [name = label, ...rest] = label.split(' · ')
  return { name, detail: rest.join(' · ') }
}

// Only shown below 100%: at full coverage "250/250" says it all
function coveragePct(run: AnalysisRunResult) {
  if (run.coverage === null || run.coverage >= 1)
    return null
  return `${Math.floor(run.coverage * 100)}%`
}

function exclusionSummary(run: AnalysisRunResult) {
  return Object.entries(run.exclusions)
    .map(([reason, count]) => `${EXCLUSION_LABELS[reason] ?? reason} ${count}`)
    .join(', ')
}

// Lowest rank score of each metric across runs, to emphasise the best run in the table
const bestScores = computed(() => {
  const best: Record<string, number> = {}
  if (okRuns.value.length < 2)
    return best
  for (const m of props.result.metrics) {
    const scores = okRuns.value
      .map(r => r.metrics[m.key]?.value)
      .filter((v): v is number => v !== null && v !== undefined)
      .map(v => metricRankScore(m, v))
    if (scores.length >= 2)
      best[m.key] = Math.min(...scores)
  }
  return best
})

// Hovering (or focusing) the trophy dims every bar but the best of each chart
const highlightBest = ref(false)

function isBest(m: MetricInfo, value: number | null | undefined) {
  return value !== null && value !== undefined && bestScores.value[m.key] === metricRankScore(m, value)
}

function excludedRowsByReason(run: AnalysisRunResult) {
  const groups: Record<string, (number | null)[]> = {}
  for (const row of run.excluded_rows)
    (groups[row.reason] ??= []).push(row.row_index)
  return groups
}

function exportCsv() {
  const header = ['run', 'execution_id', 'agent', 'n_valid', 'n_total']
  for (const m of props.result.metrics)
    header.push(m.key, `${m.key}_ci_low`, `${m.key}_ci_high`)

  const escape = (v: unknown) => {
    const s = v === null || v === undefined ? '' : String(v)
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
  }
  const lines = [header.join(',')]
  for (const run of okRuns.value) {
    const cells: unknown[] = [run.label, run.execution_id, run.agent_name, run.n_valid, run.n_total]
    for (const m of props.result.metrics) {
      const v = run.metrics[m.key]
      cells.push(v?.value, v?.ci_low, v?.ci_high)
    }
    lines.push(cells.map(escape).join(','))
  }

  const blob = new Blob([`${lines.join('\n')}\n`], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${(props.name || 'analysis').replace(/[^\w-]+/g, '_')}.csv`
  link.click()
  URL.revokeObjectURL(url)
}
</script>

<template>
  <!-- Results land once the computation is done: they fade in instead of replacing the loader in one frame -->
  <div class="enter-soft space-y-4">
    <UAlert
      v-for="warning in result.warnings"
      :key="warning"
      color="warning"
      variant="subtle"
      icon="i-ph-warning-bold"
      :title="warning"
      description="Metrics are computed independently per execution; differences may come from the data, not the model."
    />
    <UAlert
      v-for="run in failedRuns"
      :key="`failed-${run.execution_id}`"
      color="error"
      variant="subtle"
      icon="i-ph-x-circle-bold"
      :title="`${run.label}: ${run.status === 'missing' ? 'execution not found' : 'results unavailable'}`"
      :description="run.error ?? undefined"
    />

    <UCard v-if="okRuns.length" :ui="{ body: 'p-3 sm:p-3' }">
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-semibold">
              Metrics
            </h3>
            <p class="text-sm text-muted">
              Value and {{ confidencePct }}% bootstrap CI ({{ config.n_boot }} resamples) · best execution in bold
            </p>
          </div>
          <UButton
            variant="outline"
            color="neutral"
            icon="i-ph-download-simple-bold"
            size="sm"
            class="print:hidden"
            @click="exportCsv"
          >
            Export CSV
          </UButton>
        </div>
      </template>

      <div class="overflow-x-auto -mx-1 print:overflow-visible">
        <table class="metrics-table w-full text-sm">
          <thead>
            <tr class="text-left text-xs text-muted border-b border-default">
              <th class="px-1 pb-2 pr-4 font-medium">
                Execution
              </th>
              <th class="px-1 pb-2 pr-4 font-medium whitespace-nowrap">
                Rows used
              </th>
              <th
                v-for="m in result.metrics"
                :key="m.key"
                class="px-1 pb-2 pl-4 font-medium whitespace-nowrap text-right"
              >
                <UTooltip :text="m.description">
                  <span class="cursor-help">{{ m.label }}</span>
                </UTooltip>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="run in okRuns"
              :key="`${run.execution_id}-${run.agent_name}`"
              class="border-b border-muted last:border-0 align-top"
            >
              <td class="px-1 py-1.5 pr-4 max-w-72">
                <div class="truncate font-medium text-highlighted" :title="run.label">
                  {{ splitLabel(run.label).name }}
                </div>
                <div class="flex flex-wrap gap-x-1.5 text-xs text-muted">
                  <span v-if="splitLabel(run.label).detail" class="break-all">
                    {{ splitLabel(run.label).detail }}
                  </span>
                  <NuxtLink
                    :to="`/experiments/${run.experiment_id}`"
                    class="whitespace-nowrap hover:text-primary"
                  >
                    #{{ run.execution_id }} · {{ run.agent_name }}
                  </NuxtLink>
                </div>
              </td>
              <td class="px-1 py-1.5 pr-4 whitespace-nowrap">
                <div class="flex items-center gap-1.5">
                  <span v-if="run.coverage === null" class="text-dimmed">—</span>
                  <span v-else class="tabular-nums text-highlighted">
                    {{ run.n_valid }}<span class="text-muted">/{{ run.n_total }}</span>
                  </span>
                  <span v-if="coveragePct(run)" class="text-xs tabular-nums text-muted">
                    {{ coveragePct(run) }}
                  </span>
                  <UTooltip
                    v-if="isSmallSample(run.n_valid)"
                    :text="`Small sample: metrics from ${formatRows(run.n_valid)} aren’t reliable (under ${SMALL_SAMPLE_ROWS})`"
                  >
                    <UIcon name="i-ph-warning-bold" class="size-3.5 text-warning" />
                  </UTooltip>
                </div>
                <UPopover v-if="run.excluded_rows.length" :content="{ align: 'start' }">
                  <button
                    type="button"
                    class="flex items-center gap-1 text-xs hover:underline underline-offset-2 cursor-pointer"
                    :class="run.warnings.length ? 'text-warning' : 'text-muted'"
                    :aria-label="`Excluded rows for ${run.label}`"
                  >
                    {{ exclusionSummary(run) }}
                  </button>
                  <template #content>
                    <div class="p-3 text-sm space-y-2 max-w-xs">
                      <p v-for="w in run.warnings" :key="w" class="text-warning-700">
                        {{ w }}
                      </p>
                      <div
                        v-for="(rows, reason) in excludedRowsByReason(run)"
                        :key="reason"
                      >
                        <div class="font-medium">
                          {{ EXCLUSION_LABELS[reason] ?? reason }} ({{ rows.length }})
                        </div>
                        <div class="text-xs text-muted break-words">
                          Rows {{ rows.join(', ') }}
                        </div>
                      </div>
                    </div>
                  </template>
                </UPopover>
                <div v-else-if="exclusionSummary(run)" class="text-xs text-muted">
                  {{ exclusionSummary(run) }}
                </div>
              </td>
              <td
                v-for="m in result.metrics"
                :key="m.key"
                class="px-1 py-1.5 pl-4 whitespace-nowrap tabular-nums text-right"
              >
                <template v-if="run.metrics[m.key]?.value !== null && run.metrics[m.key]?.value !== undefined">
                  <div
                    :class="isBest(m, run.metrics[m.key]!.value) ? 'font-semibold text-highlighted' : 'text-default'"
                    :title="isBest(m, run.metrics[m.key]!.value) ? 'Best execution for this metric' : undefined"
                  >
                    {{ formatMetric(run.metrics[m.key]!.value) }}
                  </div>
                  <div v-if="run.metrics[m.key]!.ci_low !== null" class="text-xs text-muted">
                    [{{ formatMetric(run.metrics[m.key]!.ci_low) }}, {{ formatMetric(run.metrics[m.key]!.ci_high) }}]
                  </div>
                </template>
                <UTooltip v-else :text="run.metrics[m.key]?.undefined_reason ?? 'Undefined'">
                  <span class="text-dimmed">—</span>
                </UTooltip>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </UCard>

    <UCard v-if="okRuns.length">
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-semibold">
              Comparison
            </h3>
            <p class="text-sm text-muted">
              Bars show the value, whiskers the {{ confidencePct }}% confidence interval
            </p>
          </div>
          <UTooltip v-if="okRuns.length > 1" text="Highlight the best execution of each chart" :content="{ align: 'end' }">
            <span
              tabindex="0"
              class="inline-flex items-center gap-1.5 text-xs cursor-help select-none transition-colors print:hidden"
              :class="highlightBest ? 'text-highlighted' : 'text-muted'"
              @mouseenter="highlightBest = true"
              @mouseleave="highlightBest = false"
              @focus="highlightBest = true"
              @blur="highlightBest = false"
            >
              <UIcon name="i-ph-trophy-bold" class="size-3.5" />
              <span class="underline decoration-dotted underline-offset-4">Hover to see the best</span>
            </span>
          </UTooltip>
        </div>
      </template>
      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3 print:grid-cols-2">
        <AnalysesMetricBars
          v-for="m in result.metrics"
          :key="m.key"
          :metric="m"
          :runs="okRuns"
          :confidence="config.confidence"
          :highlight-best="highlightBest"
          class="print:break-inside-avoid"
        />
      </div>
    </UCard>

    <UCard v-if="okRuns.length">
      <template #header>
        <h3 class="font-semibold">
          {{ config.value_type === 'numeric' ? 'Predicted vs ground truth' : 'Confusion matrices' }}
        </h3>
        <p class="text-sm text-muted">
          <template v-if="config.value_type === 'numeric'">
            Dashed line is y = x; click a point to see its row, or the rows stacked on it
          </template>
          <template v-else>
            Click a cell to see the rows it counts
          </template>
        </p>
      </template>
      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3 print:grid-cols-2">
        <div v-for="run in okRuns" :key="`${run.execution_id}-${run.agent_name}`" class="print:break-inside-avoid">
          <h4 class="text-sm font-semibold text-highlighted mb-2 truncate">
            {{ run.label }}
          </h4>
          <template v-if="run.n_valid === 0">
            <p class="text-sm text-muted py-8 text-center">
              No usable rows
            </p>
          </template>
          <AnalysesScatter
            v-else-if="config.value_type === 'numeric'"
            :run="run"
            :domain="scatterDomain"
            :selected-row="panelOpen ? selectedRowOf(run) : null"
            @select="selectPoint(run, $event)"
          />
          <AnalysesConfusion
            v-else-if="run.confusion"
            :labels="run.confusion.labels"
            :matrix="run.confusion.matrix"
            :rows="run.confusion.rows"
            @select="selectPoint(run, $event)"
          />
        </div>
      </div>
    </UCard>

    <AnalysesRowPanel
      v-model:open="panelOpen"
      :run="selected?.run ?? null"
      :rows="selected?.rows ?? []"
      :index="selected?.index ?? 0"
      :truth-column="config.truth_column"
      @navigate="navigate"
    />
  </div>
</template>
