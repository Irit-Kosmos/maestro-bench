<script setup lang="ts">
import type { Agent, AgentTeam, Analysis, Dataset, Experiment, ProviderStatus } from '~/types'

definePageMeta({
  title: 'Dashboard',
})

const { data: experiments, pending: experimentsPending, refresh: refreshExperiments } = await useMyLazyFetch<Experiment[]>('/experiments')
const { data: analyses, pending: analysesPending, refresh: refreshAnalyses } = await useMyLazyFetch<Analysis[]>('/analyses')
const { data: datasets, pending: datasetsPending, refresh: refreshDatasets } = await useMyLazyFetch<Dataset[]>('/datasets')
const { data: agentTeams, pending: teamsPending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: providers, pending: providersPending } = await useMyLazyFetch<ProviderStatus[]>('/providers')

const { formatDate, formatRelativeDate } = useUIHelpers()

const isRefreshing = ref(false)
async function refresh() {
  isRefreshing.value = true
  try {
    await Promise.all([refreshExperiments(), refreshAnalyses(), refreshDatasets(), refreshTeams(), refreshAgents()])
  }
  finally {
    isRefreshing.value = false
  }
}

const recentExperiments = computed(() =>
  [...(experiments.value || [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 8),
)

function plural(count: number, noun: string) {
  return `${count} ${noun}${count === 1 ? '' : 's'}`
}

// "39 completed · 2 failed": only the statuses that actually occur
const experimentsDetail = computed(() => {
  const exps = experiments.value || []
  const order = ['running', 'pending', 'completed', 'failed'] as const
  return order
    .map(status => ({ status, count: exps.filter(e => e.status === status).length }))
    .filter(s => s.count > 0)
    .map(s => `${s.count} ${s.status}`)
    .join(' · ')
})

const providerNames: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  mistral: 'Mistral',
  groq: 'Groq',
  together: 'Together AI',
  deepseek: 'DeepSeek',
}

const configuredProviders = computed(() => (providers.value || []).filter(p => p.configured).length)
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
        <UButton to="/experiments/new" icon="i-lucide-plus" color="primary" size="sm">
          New experiment
        </UButton>
      </UTooltip>
    </AppPageActions>

    <!-- Stats -->
    <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <DashboardStatsCard
        title="Experiments"
        :value="experiments?.length ?? 0"
        :detail="experimentsDetail || 'None yet'"
        icon="i-lucide-flask-conical"
        :loading="experimentsPending"
        href="/experiments"
      />
      <DashboardStatsCard
        title="Analyses"
        :value="analyses?.length ?? 0"
        detail="Executions vs ground truth"
        icon="i-lucide-chart-column"
        :loading="analysesPending"
        href="/analyses"
      />
      <DashboardStatsCard
        title="Datasets"
        :value="datasets?.length ?? 0"
        :detail="plural(datasets?.length ?? 0, 'input file')"
        icon="i-lucide-database"
        :loading="datasetsPending"
        href="/datasets"
      />
      <DashboardStatsCard
        title="Agents"
        :value="agents?.length ?? 0"
        :detail="`in ${plural(agentTeams?.length ?? 0, 'team')}`"
        icon="i-lucide-bot"
        :loading="agentsPending || teamsPending"
        href="/agents"
      />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
      <!-- Recent experiments -->
      <section aria-labelledby="recent-title" class="lg:col-span-2 rounded-lg border border-default overflow-hidden">
        <div class="flex items-center justify-between h-11 px-4 border-b border-default">
          <h2 id="recent-title" class="text-sm font-medium text-highlighted">
            Recent experiments
          </h2>
          <UButton to="/experiments" color="neutral" variant="link" size="xs" trailing-icon="i-lucide-arrow-right">
            View all
          </UButton>
        </div>

        <!-- Loading skeleton -->
        <div v-if="experimentsPending && !experiments" class="divide-y divide-default">
          <div v-for="i in 5" :key="i" class="h-11 px-4 flex items-center gap-3">
            <USkeleton class="size-3.5 rounded-full" />
            <USkeleton class="h-3.5 w-48" />
            <USkeleton class="h-3 w-16 ms-auto" />
          </div>
        </div>

        <BaseEmptyState
          v-else-if="!recentExperiments.length"
          title="No experiments yet"
          message="Run an agent team over a dataset to see results here."
          icon="i-lucide-flask-conical"
          action-label="New experiment"
          action-to="/experiments/new"
        />

        <ul v-else class="divide-y divide-default">
          <li v-for="exp in recentExperiments" :key="exp.id">
            <NuxtLink
              :to="`/experiments/${exp.id}`"
              class="flex items-center gap-3 h-11 px-4 outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
            >
              <UIStatusIcon :status="exp.status" />
              <span class="min-w-0 truncate text-sm font-medium text-highlighted">{{ exp.name }}</span>
              <span class="shrink-0 text-xs text-dimmed tabular-nums">#{{ exp.id }}</span>
              <span v-if="exp.dataset?.name" class="hidden sm:block min-w-0 truncate text-xs text-muted">{{ exp.dataset.name }}</span>
              <UIRowCount :rows="exp.row_count" tone="quiet" class="ms-auto shrink-0 text-xs" />
              <span class="w-14 shrink-0 text-right text-xs text-muted tabular-nums" :title="formatDate(exp.created_at)">
                {{ formatRelativeDate(exp.created_at) }}
              </span>
            </NuxtLink>
          </li>
        </ul>
      </section>

      <!-- LLM providers -->
      <section aria-labelledby="providers-title" class="rounded-lg border border-default overflow-hidden">
        <div class="flex items-center justify-between h-11 px-4 border-b border-default">
          <h2 id="providers-title" class="text-sm font-medium text-highlighted">
            LLM providers
          </h2>
          <span v-if="providers?.length" class="text-xs text-muted tabular-nums">
            {{ configuredProviders }} of {{ providers.length }} ready
          </span>
        </div>

        <div v-if="providersPending && !providers" class="p-4 flex flex-col gap-3">
          <USkeleton v-for="i in 3" :key="i" class="h-4" />
        </div>

        <ul v-else-if="providers?.length" class="py-1">
          <li
            v-for="p in providers"
            :key="p.provider"
            class="flex items-center gap-2.5 h-9 px-4"
          >
            <UIcon
              :name="p.configured ? 'i-lucide-circle-check' : 'i-lucide-circle-dashed'"
              class="size-3.5 shrink-0"
              :class="p.configured ? 'text-success' : 'text-dimmed'"
              aria-hidden="true"
            />
            <span class="text-sm text-default" :class="!providerNames[p.provider] && 'capitalize'">{{ providerNames[p.provider] ?? p.provider }}</span>
            <span class="ms-auto text-xs" :class="p.configured ? 'text-toned' : 'text-muted'">
              {{ p.configured ? 'Ready' : 'API key not set' }}
            </span>
          </li>
        </ul>

        <p v-else class="px-4 py-6 text-sm text-muted">
          No providers reported by the backend.
        </p>
      </section>
    </div>
  </div>
</template>
