<script setup lang="ts">
import type { Agent, AgentTeam, Dataset, Experiment, ProviderStatus } from '~/types'

definePageMeta({
  title: 'Dashboard',
  subtitle: 'Overview of your experiments and resources',
})

const { data: experiments, pending: experimentsPending, refresh: refreshExperiments } = await useMyLazyFetch<Experiment[]>('/experiments')
const { data: datasets, pending: datasetsPending, refresh: refreshDatasets } = await useMyLazyFetch<Dataset[]>('/datasets')
const { data: agentTeams, pending: teamsPending, refresh: refreshTeams } = await useMyLazyFetch<AgentTeam[]>('/agent-teams')
const { data: agents, pending: agentsPending, refresh: refreshAgents } = await useMyLazyFetch<Agent[]>('/agents')
const { data: providers, pending: providersPending } = await useMyLazyFetch<ProviderStatus[]>('/providers')

const { getStatusColor, formatDate } = useUIHelpers()

async function refresh() {
  await Promise.all([refreshExperiments(), refreshDatasets(), refreshTeams(), refreshAgents()])
}

const datasetsCount = computed(() => datasets.value?.length || 0)
const agentTeamsCount = computed(() => agentTeams.value?.length || 0)
const agentsCount = computed(() => agents.value?.length || 0)
const isAdditionalStatsLoading = computed(() => datasetsPending.value || teamsPending.value || agentsPending.value)
const recentExperiments = computed(() => experiments.value?.slice(0, 5) || [])
const totalExperiments = computed(() => experiments.value?.length || 0)

const statusBreakdown = computed(() => {
  const exps = experiments.value || []
  return {
    completed: exps.filter(e => e.status === 'completed').length,
    running: exps.filter(e => e.status === 'running').length,
    failed: exps.filter(e => e.status === 'failed').length,
    pending: exps.filter(e => e.status === 'pending').length,
  }
})

const quickActions = [
  { label: 'New Experiment', icon: 'i-lucide-plus', to: '/experiments/new', primary: true },
  { label: 'All Experiments', icon: 'i-lucide-flask-conical', to: '/experiments' },
  { label: 'Datasets', icon: 'i-lucide-database', to: '/datasets' },
  { label: 'Agents', icon: 'i-lucide-bot', to: '/agents' },
]
</script>

<template>
  <BasePageContent :loading="false">
    <!-- Header -->
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-neutral-900">
        Overview
      </h1>
      <p class="text-sm text-neutral-400 mt-0.5">
        Your experiments and resources at a glance
      </p>
    </div>

    <!-- Stats Grid -->
    <div class="grid grid-cols-3 gap-3 mb-8">
      <DashboardStatsCard
        title="Experiments"
        :value="totalExperiments"
        icon="i-lucide-activity"
        icon-color="text-indigo-400"
        :loading="experimentsPending"
        href="/experiments"
      />
      <DashboardStatsCard
        title="Datasets"
        :value="datasetsCount"
        icon="i-lucide-database"
        icon-color="text-violet-400"
        :loading="isAdditionalStatsLoading"
        href="/datasets"
      />
      <DashboardStatsCard
        title="Teams & Agents"
        :value="`${agentTeamsCount} teams · ${agentsCount} agents`"
        icon="i-lucide-users"
        icon-color="text-emerald-400"
        :loading="isAdditionalStatsLoading"
        href="/agents"
      />
    </div>

    <!-- Main 2-col layout -->
    <div class="grid grid-cols-3 gap-6">
      <!-- Left: Recent Experiments -->
      <div class="col-span-2 flex flex-col gap-4">
        <div class="border border-neutral-200 rounded-lg bg-white overflow-hidden">
          <!-- Table header -->
          <div class="flex items-center justify-between px-5 py-3.5 border-b border-neutral-100">
            <span class="text-sm font-medium text-neutral-700">Recent Experiments</span>
            <div class="flex items-center gap-3">
              <UButton
                class="text-neutral-400 hover:text-neutral-600 transition-colors"
                title="Refresh"
                icon="i-lucide-refresh-cw"
                size="sm"
                variant="ghost"
                @click="refresh"
              />
              <NuxtLink to="/experiments" class="text-xs text-neutral-400 hover:text-indigo-600 transition-colors font-medium">
                View all →
              </NuxtLink>
            </div>
          </div>

          <!-- Loading skeleton -->
          <div v-if="experimentsPending" class="divide-y divide-neutral-100">
            <div v-for="i in 5" :key="i" class="px-5 py-3.5 flex items-center gap-4">
              <div class="flex-1 space-y-1.5">
                <div class="h-3.5 w-36 bg-neutral-100 rounded animate-pulse" />
                <div class="h-3 w-20 bg-neutral-100 rounded animate-pulse" />
              </div>
              <div class="h-5 w-16 bg-neutral-100 rounded animate-pulse" />
              <div class="h-3 w-28 bg-neutral-100 rounded animate-pulse" />
            </div>
          </div>

          <!-- Empty state -->
          <div v-else-if="!recentExperiments.length" class="px-5 py-12 text-center">
            <UIcon name="i-lucide-flask-conical" class="size-8 text-neutral-200 mx-auto mb-3" />
            <p class="text-sm text-neutral-400">
              No experiments yet
            </p>
            <NuxtLink to="/experiments/new" class="mt-3 inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700">
              <UIcon name="i-lucide-plus" class="size-3" />
              Create your first experiment
            </NuxtLink>
          </div>

          <!-- Experiment rows -->
          <div v-else class="divide-y divide-neutral-100">
            <NuxtLink
              v-for="exp in recentExperiments"
              :key="exp.id"
              :to="`/experiments/${exp.id}`"
              class="flex items-center gap-4 px-5 py-3.5 hover:bg-neutral-50 transition-colors group"
            >
              <!-- Name + ID -->
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-neutral-900 truncate group-hover:text-indigo-600 transition-colors">
                  {{ exp.name }}
                </div>
                <div class="flex items-center gap-2 mt-0.5">
                  <span class="text-xs text-neutral-400 font-mono">#{{ exp.id }}</span>
                  <span v-if="exp.dataset?.name" class="text-xs text-neutral-400">· {{ exp.dataset.name }}</span>
                </div>
              </div>

              <!-- Status -->
              <UBadge
                :color="getStatusColor(exp.status || 'pending')"
                variant="soft"
                size="sm"
              >
                {{ exp.status || 'pending' }}
              </UBadge>

              <!-- Date -->
              <span class="text-xs text-neutral-400 whitespace-nowrap tabular-nums shrink-0">
                {{ formatDate(exp.created_at) }}
              </span>

              <!-- Arrow -->
              <UIcon name="i-lucide-chevron-right" class="size-3.5 text-neutral-300 group-hover:text-neutral-400 shrink-0" />
            </NuxtLink>
          </div>
        </div>

        <!-- Status breakdown -->
        <div v-if="!experimentsPending && totalExperiments > 0" class="grid grid-cols-4 gap-2">
          <div
            v-for="(count, status) in statusBreakdown"
            :key="status"
            class="flex items-center gap-2.5 px-3 py-2.5 rounded-lg border border-neutral-200 bg-white"
          >
            <span
              class="size-1.5 rounded-full shrink-0"
              :class="{
                'bg-emerald-400': status === 'completed',
                'bg-blue-400': status === 'running',
                'bg-red-400': status === 'failed',
                'bg-amber-400': status === 'pending',
              }"
            />
            <div class="min-w-0">
              <div class="text-sm font-semibold text-neutral-800 tabular-nums leading-none">
                {{ count }}
              </div>
              <div class="text-xs text-neutral-400 capitalize mt-0.5">
                {{ status }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Quick Actions + Providers -->
      <div class="col-span-1 flex flex-col gap-4">
        <!-- Quick Actions -->
        <div class="border border-neutral-200 rounded-lg bg-white overflow-hidden">
          <div class="px-5 py-3.5 border-b border-neutral-100">
            <span class="text-sm font-medium text-neutral-700">Quick Actions</span>
          </div>
          <div class="p-3 flex flex-col gap-1">
            <NuxtLink
              v-for="action in quickActions"
              :key="action.label"
              :to="action.to"
              class="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors"
              :class="action.primary
                ? 'border border-primary-300 bg-primary-100 text-primary-600 hover:bg-primary-200 font-medium'
                : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'"
            >
              <UIcon :name="action.icon" class="size-3.5 shrink-0" />
              {{ action.label }}
              <UIcon v-if="!action.primary" name="i-lucide-arrow-up-right" class="size-3.5 text-neutral-500 ml-auto" />
            </NuxtLink>
          </div>
        </div>

        <!-- LLM Providers -->
        <div v-if="!providersPending && providers?.length" class="border border-neutral-200 rounded-lg bg-white overflow-hidden">
          <div class="px-5 py-3.5 border-b border-neutral-100">
            <span class="text-sm font-medium text-neutral-700">LLM Providers</span>
          </div>
          <div class="p-3 flex flex-col gap-1">
            <div
              v-for="p in providers"
              :key="p.provider"
              class="flex items-center justify-between px-3 py-2 rounded-md"
            >
              <div class="flex items-center gap-2.5">
                <span
                  class="size-1.5 rounded-full shrink-0"
                  :class="p.configured ? 'bg-emerald-400' : 'bg-neutral-300'"
                />
                <span class="text-sm text-neutral-700 capitalize">{{ p.provider }}</span>
              </div>
              <span class="text-xs" :class="p.configured ? 'text-emerald-500' : 'text-neutral-400'">
                {{ p.configured ? 'ready' : 'not set' }}
              </span>
            </div>
          </div>
        </div>

        <!-- Provider loading skeleton -->
        <div v-else-if="providersPending" class="border border-neutral-200 rounded-lg bg-white overflow-hidden">
          <div class="px-5 py-3.5 border-b border-neutral-100">
            <div class="h-4 w-24 bg-neutral-100 rounded animate-pulse" />
          </div>
          <div class="p-5 flex flex-col gap-2.5">
            <div v-for="i in 3" :key="i" class="h-4 bg-neutral-100 rounded animate-pulse" />
          </div>
        </div>
      </div>
    </div>
  </BasePageContent>
</template>
