<script setup lang="ts">
import type { Analysis, Batch, Dashboard, ProviderStatus } from '~/types'

definePageMeta({
  title: 'Dashboard',
})

const range = useDashboardRange()
// The previous figures stay up until the new period's arrive
const { data: dashboard, status, error: dashboardError, refresh: refreshDashboard } = await useMyLazyFetch<Dashboard>('/dashboard', {
  query: computed(() => ({ range: range.value })),
})
const { data: batches, error: batchesError, refresh: refreshBatches } = await useMyLazyFetch<Batch[]>('/batches')
const { data: analyses, error: analysesError, refresh: refreshAnalyses } = await useMyLazyFetch<Analysis[]>('/analyses')
const { data: providers } = await useMyLazyFetch<ProviderStatus[]>('/providers')

const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

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

// Runs are watched from here as well: the running banner, the figures and the lists follow them
useRefreshOnRunStatus(() => Promise.all([refreshDashboard(), refreshBatches()]))

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
          icon="i-ph-arrows-clockwise-bold"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="Refresh"
          :loading="isRefreshing"
          @click="refresh"
        />
      </UTooltip>
      <UTooltip v-if="canEdit" text="New experiment" :kbds="['C']">
        <UButton to="/experiments/new" icon="i-ph-plus-bold" color="neutral" variant="soft" size="sm">
          New experiment
        </UButton>
      </UTooltip>
      <UIGuardedButton v-else to="/experiments/new" icon="i-ph-plus-bold" color="neutral" variant="soft" size="sm">
        New experiment
      </UIGuardedButton>
    </AppPageActions>

    <NuxtLink
      v-if="noProvider"
      to="/settings"
      class="flex items-center gap-2.5 h-10 px-4 rounded-lg border border-warning/30 bg-warning/10 text-sm text-toned outline-none hover:bg-warning/15 focus-visible:ring-2 focus-visible:ring-inverted"
    >
      <UIcon name="i-ph-warning-bold" class="size-4 shrink-0 text-warning" aria-hidden="true" />
      <span class="min-w-0 truncate">No LLM provider is set up, so experiments can’t run.</span>
      <span class="ms-auto shrink-0 inline-flex items-center gap-1 text-xs font-medium text-highlighted">
        Open settings
        <UIcon name="i-ph-arrow-right-bold" class="size-3.5" aria-hidden="true" />
      </span>
    </NuxtLink>

    <BaseErrorState
      v-if="!dashboard && dashboardError"
      :kind="fetchErrorKind(dashboardError)"
      @retry="refresh()"
    />

    <template v-else>
      <!-- Appears and leaves on its own as runs start and end: the cards below glide instead of jumping (gap-6 = 1.5rem) -->
      <Transition name="reveal">
        <div v-if="dashboard?.activity.active.length" class="reveal [--reveal-gap:1.5rem]">
          <DashboardRunning :active="dashboard.activity.active" />
        </div>
      </Transition>

      <DashboardActivity
        v-model:range="range"
        :activity="dashboard?.activity"
        :loading="!dashboard"
        :refreshing="!!dashboard && status === 'pending'"
      />

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
          icon="i-ph-flask-bold"
          action-label="New experiment"
          action-to="/experiments/new"
          action-requires="editor"
        />
      </BaseSection>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
        <BaseSection title="Batches" to="/batches">
          <ul v-if="recentBatches.length" class="divide-y divide-default">
            <li v-for="batch in recentBatches" :key="batch.id">
              <DashboardListRow :to="`/batches/${batch.id}`">
                <UIStatusIcon :status="batch.status" />
                <span class="min-w-0 truncate text-sm font-medium text-highlighted">{{ batch.name }}</span>
                <span class="shrink-0 text-xs text-muted tabular-nums">#{{ batch.id }}</span>
                <span class="ms-auto shrink-0 text-xs text-muted tabular-nums">
                  {{ batch.counts.completed ?? 0 }} / {{ batch.experiments.length }} done
                </span>
                <span class="w-14 shrink-0 text-right text-xs text-muted" :title="formatDate(batch.created_at)">
                  {{ formatRelativeDate(batch.created_at) }}
                </span>
              </DashboardListRow>
            </li>
          </ul>
          <p v-else class="px-4 py-6 text-sm text-muted">
            {{ batches ? 'No batches yet. Vary models, prompts or temperatures from any experiment.' : batchesError ? 'Couldn’t load the batches.' : 'Loading…' }}
          </p>
        </BaseSection>

        <BaseSection title="Analyses" to="/analyses">
          <ul v-if="recentAnalyses.length" class="divide-y divide-default">
            <li v-for="analysis in recentAnalyses" :key="analysis.id">
              <DashboardListRow :to="`/analyses/${analysis.id}`">
                <UIcon name="i-ph-chart-bar-bold" class="size-3.5 shrink-0 text-muted" aria-hidden="true" />
                <span class="min-w-0 truncate text-sm font-medium text-highlighted">{{ analysis.name }}</span>
                <span class="shrink-0 text-xs text-muted tabular-nums">#{{ analysis.id }}</span>
                <span class="ms-auto shrink-0 text-xs text-muted tabular-nums">
                  {{ analysis.runs.length }} {{ analysis.runs.length === 1 ? 'execution' : 'executions' }}
                </span>
                <span class="w-14 shrink-0 text-right text-xs text-muted" :title="formatDate(analysis.updated_at)">
                  {{ formatRelativeDate(analysis.updated_at) }}
                </span>
              </DashboardListRow>
            </li>
          </ul>
          <p v-else class="px-4 py-6 text-sm text-muted">
            {{ analyses ? 'No analyses yet. Compare executions to a ground truth.' : analysesError ? 'Couldn’t load the analyses.' : 'Loading…' }}
          </p>
        </BaseSection>
      </div>
    </template>
  </div>
</template>
