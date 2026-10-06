<script setup lang="ts">
import type { ExecutionListItem, RunState } from '~/types'

// One execution at a glance, to triage a list without leaving it: how it ended, what it ran on
// and with, what it cost. The way into the experiment, the results and an analysis is in the footer.
const props = defineProps<{
  execution: ExecutionListItem | null
  /** Live state of the execution while it runs */
  run?: RunState | null
  /** Position among the executions currently shown */
  index: number
  total: number
  analyzable: boolean
}>()

const emit = defineEmits<{
  navigate: [delta: number]
  analyze: []
  download: []
}>()

const open = defineModel<boolean>('open', { default: false })

const { formatDate, formatRelativeDate } = useUIHelpers()

const agents = computed(() => props.execution?.agents ?? [])

// Typing in a field is left alone: these only fire outside inputs
defineShortcuts({
  j: () => open.value && emit('navigate', 1),
  k: () => open.value && emit('navigate', -1),
})
</script>

<template>
  <USlideover
    v-model:open="open"
    :title="execution ? `Execution #${execution.id}` : 'Execution'"
    :description="execution ? `${index + 1} of ${total.toLocaleString('en-US')}` : undefined"
    :ui="{ content: 'max-w-md' }"
  >
    <template #body>
      <div v-if="execution" class="flex flex-col gap-5">
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap items-center gap-x-3 gap-y-1">
            <UIStatusBadge :status="execution.status" />
            <span class="text-xs text-muted" :title="formatDate(execution.started_at)">
              Started {{ formatRelativeDate(execution.started_at) }}
            </span>
          </div>
          <UIRunProgress v-if="run && run.execution_id === execution.id" :run="run" />
        </div>

        <dl class="grid grid-cols-[6.5rem_minmax(0,1fr)] gap-x-3 gap-y-2.5 text-sm">
          <dt class="text-muted">
            Experiment
          </dt>
          <dd class="min-w-0">
            <NuxtLink
              :to="{ path: `/experiments/${execution.experiment_id}`, hash: '#executions' }"
              class="inline-flex max-w-full items-center gap-1 rounded font-medium text-highlighted outline-none hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
            >
              <span class="truncate">{{ execution.experiment_name }}</span>
              <UIcon name="i-ph-arrow-up-right-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
            </NuxtLink>
          </dd>

          <template v-if="execution.batch_id">
            <dt class="text-muted">
              Batch
            </dt>
            <dd class="min-w-0">
              <NuxtLink
                :to="`/batches/${execution.batch_id}`"
                class="inline-flex max-w-full items-center gap-1 rounded text-toned outline-none hover:text-highlighted hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
              >
                <UIcon name="i-ph-arrows-split-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
                <span class="truncate">{{ execution.batch_name }}</span>
              </NuxtLink>
            </dd>
          </template>

          <dt class="text-muted">
            Dataset
          </dt>
          <dd class="min-w-0 truncate text-toned">
            {{ execution.dataset_name || '—' }}
          </dd>

          <dt class="text-muted">
            Rows
          </dt>
          <dd class="flex flex-wrap items-baseline gap-x-2 tabular-nums">
            <UIRowCount :rows="execution.row_count" tone="quiet" />
            <span v-if="execution.rows_failed" class="text-xs text-error">{{ execution.rows_failed }} failed</span>
          </dd>

          <dt class="text-muted">
            Duration
          </dt>
          <dd class="tabular-nums text-toned">
            {{ formatElapsed(execution.duration_seconds) }}
          </dd>

          <dt class="text-muted">
            Tokens
          </dt>
          <dd class="tabular-nums text-toned" :title="formatCount(execution.total_tokens)">
            {{ formatTokens(execution.total_tokens) }}
          </dd>

          <dt class="text-muted">
            Cost
          </dt>
          <dd class="tabular-nums text-toned" :title="formatCostPrecise(execution.total_cost_usd)">
            {{ formatCost(execution.total_cost_usd) }}
          </dd>
        </dl>

        <section v-if="agents.length" aria-labelledby="execution-agents">
          <h3 id="execution-agents" class="mb-2 text-xs font-medium text-muted">
            {{ agents.length > 1 ? 'Agents, in the order they ran' : 'Agent' }}
          </h3>
          <ol class="divide-y divide-default overflow-hidden rounded-lg border border-default">
            <li v-for="(agent, i) in agents" :key="i" class="relative flex items-start gap-3 px-3 py-2.5" :class="!!agent.agent_id && 'hover:bg-elevated/50'">
              <span
                v-if="agents.length > 1"
                class="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full border border-default text-xs font-medium text-toned tabular-nums"
              >
                <span class="sr-only">Step </span>{{ i + 1 }}
              </span>
              <div class="min-w-0">
                <!-- A deleted agent has only its snapshot left, so there is nothing to open -->
                <NuxtLink
                  v-if="agent.agent_id"
                  :to="{ path: '/agents', query: { agent: agent.agent_id } }"
                  class="flex items-center gap-1 text-sm font-medium text-highlighted outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-inverted"
                  :title="`Open agent ${agent.name}`"
                >
                  <span class="truncate">{{ agent.name }}</span>
                  <UIcon name="i-ph-arrow-up-right-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
                </NuxtLink>
                <p v-else class="truncate text-sm font-medium text-highlighted">
                  {{ agent.name }}
                  <span class="text-xs font-normal text-muted">(deleted)</span>
                </p>
                <p v-if="agent.kind === 'aggregator'" class="mt-0.5 flex min-w-0 items-center gap-1 text-xs text-muted">
                  <UIcon name="i-ph-function-bold" class="size-3 shrink-0" aria-hidden="true" />
                  Aggregator
                </p>
                <p v-else class="mt-0.5 flex min-w-0 items-center gap-1 text-xs text-muted">
                  <span class="shrink-0">{{ agent.prompt }} v{{ agent.prompt_version }}</span>
                  <span aria-hidden="true">·</span>
                  <ModelsLabel :name="agent.model" :provider="agent.provider" />
                </p>
              </div>
            </li>
          </ol>
        </section>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-between gap-2">
        <div class="flex items-center gap-1">
          <UTooltip text="Previous execution" :kbds="['k']">
            <UButton
              icon="i-ph-caret-up-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Previous execution"
              :disabled="index <= 0"
              @click="emit('navigate', -1)"
            />
          </UTooltip>
          <UTooltip text="Next execution" :kbds="['j']">
            <UButton
              icon="i-ph-caret-down-bold"
              color="neutral"
              variant="outline"
              size="sm"
              aria-label="Next execution"
              :disabled="index >= total - 1"
              @click="emit('navigate', 1)"
            />
          </UTooltip>
        </div>

        <div v-if="execution" class="flex items-center gap-1">
          <UTooltip v-if="execution.has_results" text="Download results">
            <UButton
              icon="i-ph-download-simple-bold"
              color="neutral"
              variant="ghost"
              size="sm"
              :aria-label="`Download results of execution #${execution.id}`"
              @click="emit('download')"
            />
          </UTooltip>
          <UIGuardedButton
            icon="i-ph-chart-bar-bold"
            color="neutral"
            variant="soft"
            size="sm"
            :disabled="!analyzable"
            @click="emit('analyze')"
          >
            Analyze
          </UIGuardedButton>
        </div>
      </div>
    </template>
  </USlideover>
</template>
