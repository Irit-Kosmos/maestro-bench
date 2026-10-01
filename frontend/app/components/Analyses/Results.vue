<script setup lang="ts">
import type { AnalysisConfig, AnalysisResult, AnalysisRunResult } from '~/types'
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

function coverageLabel(run: AnalysisRunResult) {
  if (run.coverage === null)
    return '—'
  return `${run.n_valid}/${run.n_total} (${Math.round(run.coverage * 100)}%)`
}

function exclusionSummary(run: AnalysisRunResult) {
  return Object.entries(run.exclusions)
    .map(([reason, count]) => `${EXCLUSION_LABELS[reason] ?? reason}: ${count}`)
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
  <div class="space-y-4">
    <UAlert
      v-for="warning in result.warnings"
      :key="warning"
      color="warning"
      variant="subtle"
      icon="i-lucide-triangle-alert"
      :title="warning"
      description="Metrics are computed independently per run; differences may come from the data, not the model."
    />
    <UAlert
      v-for="run in failedRuns"
      :key="`failed-${run.execution_id}`"
      color="error"
      variant="subtle"
      icon="i-lucide-circle-x"
      :title="`${run.label}: ${run.status === 'missing' ? 'execution not found' : 'results unavailable'}`"
      :description="run.error ?? undefined"
    />

    <UCard v-if="okRuns.length">
      <template #header>
        <div class="flex items-center justify-between">
          <div>
            <h3 class="font-semibold">
              Metrics
            </h3>
            <p class="text-sm text-muted">
              Value [{{ confidencePct }}% bootstrap CI, {{ config.n_boot }} resamples]
            </p>
          </div>
          <UButton
            variant="outline"
            color="neutral"
            icon="i-lucide-download"
            size="sm"
            @click="exportCsv"
          >
            Export CSV
          </UButton>
        </div>
      </template>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="text-left text-muted border-b border-default">
              <th class="py-2 pr-4 font-medium">
                Run
              </th>
              <th class="py-2 pr-4 font-medium">
                Rows used
              </th>
              <th
                v-for="m in result.metrics"
                :key="m.key"
                class="py-2 pr-4 font-medium whitespace-nowrap"
              >
                <UTooltip :text="m.description">
                  <span class="underline decoration-dotted underline-offset-4">{{ m.label }}</span>
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
              <td class="py-2 pr-4">
                <div class="font-medium text-highlighted">
                  {{ run.label }}
                </div>
                <NuxtLink
                  :to="`/experiments/${run.experiment_id}`"
                  class="text-xs text-muted hover:text-primary"
                >
                  Execution #{{ run.execution_id }} · {{ run.agent_name }}
                </NuxtLink>
              </td>
              <td class="py-2 pr-4 whitespace-nowrap">
                <div class="flex items-center gap-1">
                  <span class="tabular-nums">{{ coverageLabel(run) }}</span>
                  <UTooltip
                    v-if="isSmallSample(run.n_valid)"
                    :text="`Small sample: metrics from ${formatRows(run.n_valid)} aren’t reliable (under ${SMALL_SAMPLE_ROWS})`"
                  >
                    <UBadge color="warning" variant="soft" size="sm" icon="i-lucide-triangle-alert">
                      Small sample
                    </UBadge>
                  </UTooltip>
                  <UPopover v-if="run.excluded_rows.length">
                    <UButton
                      size="xs"
                      variant="ghost"
                      :color="run.warnings.length ? 'warning' : 'neutral'"
                      :icon="run.warnings.length ? 'i-lucide-triangle-alert' : 'i-lucide-info'"
                      :aria-label="`Excluded rows for ${run.label}`"
                    />
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
                </div>
                <div
                  v-for="line in exclusionSummary(run)"
                  :key="line"
                  class="text-xs text-muted"
                >
                  {{ line }}
                </div>
              </td>
              <td
                v-for="m in result.metrics"
                :key="m.key"
                class="py-2 pr-4 whitespace-nowrap tabular-nums"
              >
                <template v-if="run.metrics[m.key]?.value !== null && run.metrics[m.key]?.value !== undefined">
                  <span class="font-medium text-highlighted">{{ formatMetric(run.metrics[m.key]!.value) }}</span>
                  <span v-if="run.metrics[m.key]!.ci_low !== null" class="text-muted">
                    [{{ formatMetric(run.metrics[m.key]!.ci_low) }}, {{ formatMetric(run.metrics[m.key]!.ci_high) }}]
                  </span>
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
        <h3 class="font-semibold">
          Comparison
        </h3>
        <p class="text-sm text-muted">
          Bars show the value, whiskers the {{ confidencePct }}% confidence interval
        </p>
      </template>
      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        <AnalysesMetricBars
          v-for="m in result.metrics"
          :key="m.key"
          :metric="m"
          :runs="okRuns"
          :confidence="config.confidence"
        />
      </div>
    </UCard>

    <UCard v-if="okRuns.length">
      <template #header>
        <h3 class="font-semibold">
          {{ config.value_type === 'numeric' ? 'Predicted vs ground truth' : 'Confusion matrices' }}
        </h3>
        <p v-if="config.value_type === 'numeric'" class="text-sm text-muted">
          Points are jittered to show overlapping values; dashed line is y = x
        </p>
      </template>
      <div class="grid gap-6 md:grid-cols-2 xl:grid-cols-3">
        <div v-for="run in okRuns" :key="`${run.execution_id}-${run.agent_name}`">
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
          />
          <AnalysesConfusion
            v-else-if="run.confusion"
            :labels="run.confusion.labels"
            :matrix="run.confusion.matrix"
          />
        </div>
      </div>
    </UCard>
  </div>
</template>
