<script setup lang="ts">
import type { Analysis, Batch, Dashboard, ProviderStatus } from '~/types'

definePageMeta({
  title: 'Dashboard',
})

const { data: dashboard, refresh: refreshDashboard } = await useMyLazyFetch<Dashboard>('/dashboard')
const { data: batches, refresh: refreshBatches } = await useMyLazyFetch<Batch[]>('/batches')
const { data: analyses, refresh: refreshAnalyses } = await useMyLazyFetch<Analysis[]>('/analyses')
const { data: providers } = await useMyLazyFetch<ProviderStatus[]>('/providers')

const { formatDate, formatRelativeDate } = useUIHelpers()

const isRefreshing = ref(false)
async function refresh() {
  isRefreshing.value = true
  try {
    await Promise.all([refreshDashboard(), refreshBatches(), refreshAnalyses()])
  }
  finally {
    isRefreshing.value = false
  }
}

// Runs are watched from here as well: refresh quietly while any is going
const active = computed(() => dashboard.value?.activity.active ?? 0)
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  timer = setInterval(() => {
    if (active.value) {
      refreshDashboard()
      refreshBatches()
    }
  }, 5000)
})
onBeforeUnmount(() => clearInterval(timer))

function latest<T extends { created_at: string }>(items: readonly T[] | null | undefined) {
  return [...(items ?? [])].sort((a, b) => parseApiDate(b.created_at).getTime() - parseApiDate(a.created_at).getTime()).slice(0, 5)
}

const recentBatches = computed(() => latest(batches.value))
const recentAnalyses = computed(() => latest(analyses.value))

// Nothing can run without a key: the one provider fact worth raising here
const noProvider = computed(() => !!providers.value?.length && !providers.value.some(p => p.configured))
</script>

<template>
  <div class="flex flex-col gap-6">
    <AppPageActions>
      <UTooltip text="Refresh">
        <UButton
          icon="i-lucide-refresh-cw"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="Refresh"
          :loading="isRefreshing"
          @click="refresh"
        />
      </UTooltip>
      <UTooltip text="New experiment" :kbds="['C']">
        <UButton to="/experiments/new" icon="i-lucide-plus" color="neutral" variant="soft" size="sm">
          New experiment
        </UButton>
      </UTooltip>
    </AppPageActions>

    <NuxtLink
      v-if="noProvider"
      to="/settings"
      class="flex items-center gap-2.5 h-10 px-4 rounded-lg border border-warning/30 bg-warning/10 text-sm text-toned outline-none hover:bg-warning/15 focus-visible:ring-2 focus-visible:ring-primary"
    >
      <UIcon name="i-lucide-triangle-alert" class="size-4 shrink-0 text-warning" aria-hidden="true" />
      <span class="min-w-0 truncate">No LLM provider is set up, so experiments can’t run.</span>
      <span class="ms-auto shrink-0 inline-flex items-center gap-1 text-xs font-medium text-highlighted">
        Open settings
        <UIcon name="i-lucide-arrow-right" class="size-3.5" aria-hidden="true" />
      </span>
    </NuxtLink>

    <DashboardActivity :activity="dashboard?.activity" :loading="!dashboard" />

    <BaseSection title="Recent experiments" to="/experiments">
      <DashboardRecentExperiments
        v-if="!dashboard || dashboard.recent_experiments.length"
        :experiments="dashboard?.recent_experiments ?? []"
        :loading="!dashboard"
      />
      <BaseEmptyState
        v-else
        title="No experiments yet"
        message="Run an agent team over a dataset to see results here."
        icon="i-lucide-flask-conical"
        action-label="New experiment"
        action-to="/experiments/new"
      />
    </BaseSection>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
      <BaseSection title="Batches" to="/batches">
        <ul v-if="recentBatches.length" class="divide-y divide-default">
          <li v-for="batch in recentBatches" :key="batch.id">
            <DashboardListRow :to="`/batches/${batch.id}`">
              <UIStatusIcon :status="batch.status" />
              <span class="min-w-0 truncate text-sm font-medium text-highlighted">{{ batch.name }}</span>
              <span class="shrink-0 text-xs text-dimmed tabular-nums">#{{ batch.id }}</span>
              <span class="ms-auto shrink-0 text-xs text-muted tabular-nums">
                {{ batch.counts.completed ?? 0 }} / {{ batch.experiments.length }} done
              </span>
              <span class="w-14 shrink-0 text-right text-xs text-muted tabular-nums" :title="formatDate(batch.created_at)">
                {{ formatRelativeDate(batch.created_at) }}
              </span>
            </DashboardListRow>
          </li>
        </ul>
        <p v-else class="px-4 py-6 text-sm text-muted">
          {{ batches ? 'No batches yet. Vary models, prompts or temperatures from any experiment.' : 'Loading…' }}
        </p>
      </BaseSection>

      <BaseSection title="Analyses" to="/analyses">
        <ul v-if="recentAnalyses.length" class="divide-y divide-default">
          <li v-for="analysis in recentAnalyses" :key="analysis.id">
            <DashboardListRow :to="`/analyses/${analysis.id}`">
              <UIcon name="i-lucide-chart-column" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
              <span class="min-w-0 truncate text-sm font-medium text-highlighted">{{ analysis.name }}</span>
              <span class="shrink-0 text-xs text-dimmed tabular-nums">#{{ analysis.id }}</span>
              <span class="ms-auto shrink-0 text-xs text-muted tabular-nums">
                {{ analysis.runs.length }} {{ analysis.runs.length === 1 ? 'run' : 'runs' }}
              </span>
              <span class="w-14 shrink-0 text-right text-xs text-muted tabular-nums" :title="formatDate(analysis.updated_at)">
                {{ formatRelativeDate(analysis.updated_at) }}
              </span>
            </DashboardListRow>
          </li>
        </ul>
        <p v-else class="px-4 py-6 text-sm text-muted">
          {{ analyses ? 'No analyses yet. Compare executions to a ground truth.' : 'Loading…' }}
        </p>
      </BaseSection>
    </div>
  </div>
</template>
