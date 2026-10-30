<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Analysis, Batch, Dashboard, ProviderStatus } from '~/types'
import { DASHBOARD_RANGES } from '~/utils/dashboard'

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
const { studies, refreshStudies } = useStudies()

const { canEdit } = useCurrentWorkspace()

const isRefreshing = ref(false)
async function refresh() {
  isRefreshing.value = true
  try {
    await Promise.all([refreshDashboard(), refreshBatches(), refreshAnalyses(), refreshStudies()])
  }
  finally {
    isRefreshing.value = false
  }
}

// Runs are watched from here as well: the running banner, the figures and the lists follow them
useRefreshOnRunStatus(() => Promise.all([refreshDashboard(), refreshBatches()]))

// Rows are 48px (two lines) plus their divider. Besides its rows, a block has its borders, its
// 44px header and its 32px column labels.
const experimentsCell = useTemplateRef<HTMLElement>('experimentsCell')
const workCell = useTemplateRef<HTMLElement>('workCell')
const experimentRows = useFittingRows(experimentsCell, 49, 7, 2 + 44 + 32)
const workRows = useFittingRows(workCell, 49, 7, 2 + 44 + 32)

// Nothing can run without a key: the one provider fact worth raising here
const noProvider = computed(() => !!providers.value?.length && !providers.value.some(p => p.configured))
</script>

<template>
  <div class="flex flex-col gap-6 xl:flex-1">
    <AppPageActions>
      <UButton
        data-tooltip="Refresh"
        icon="i-ph-arrows-clockwise-bold"
        color="neutral"
        variant="ghost"
        size="sm"
        aria-label="Refresh"
        :loading="isRefreshing"
        @click="refresh"
      />
      <UButton v-if="canEdit" data-tooltip="New experiment" data-tooltip-kbds="C" to="/experiments/new" icon="i-ph-plus-bold" color="neutral" variant="soft" size="sm">
        New experiment
      </UButton>
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

      <!-- The period's figures and the models they ran on, under the period they follow -->
      <section aria-labelledby="dashboard-activity" class="flex shrink-0 flex-col gap-2">
        <div class="flex items-center justify-between gap-3">
          <h2 id="dashboard-activity" class="text-sm font-medium text-highlighted">
            Activity
          </h2>
          <UTabs
            v-model="range"
            :items="DASHBOARD_RANGES.map(r => ({ label: r.label, value: r.value }))"
            :content="false"
            variant="pill"
            color="neutral"
            size="xs"
            :ui="{
              indicator: 'bg-default ring ring-default shadow-xs',
              trigger: 'data-[state=active]:text-highlighted',
            }"
            aria-label="Period"
          />
        </div>
        <div class="grid grid-cols-1 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] gap-6">
          <DashboardActivity
            v-model:range="range"
            :activity="dashboard?.activity"
            :loading="!dashboard"
            :refreshing="!!dashboard && status === 'pending'"
          />
          <DashboardModels
            :models="dashboard?.activity.models ?? []"
            :loading="!dashboard"
            class="motion-safe:transition-opacity"
            :class="{ 'opacity-60': !!dashboard && status === 'pending' }"
          />
        </div>
      </section>

      <!-- On wide screens both lists show as many rows as the rest of the height holds: no scrolling.
           The cells are measured, and each block stays as tall as its rows -->
      <div class="grid grid-cols-1 xl:min-h-80 xl:flex-1 xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)] xl:grid-rows-[minmax(0,1fr)] gap-6">
        <div ref="experimentsCell" class="min-h-0">
          <BaseSection title="Recent experiments" to="/experiments">
            <DashboardRecentExperiments
              v-if="!dashboard || dashboard.recent_experiments.length"
              :experiments="dashboard?.recent_experiments ?? []"
              :loading="!dashboard"
              :max-rows="experimentRows"
            />
            <BaseEmptyState
              v-else
              title="No experiments yet"
              message="Run agents over a dataset to see results here."
              icon="i-ph-flask-bold"
              action-label="New experiment"
              action-to="/experiments/new"
              action-requires="editor"
            />
          </BaseSection>
        </div>

        <div ref="workCell" class="min-h-0">
          <BaseSection title="Recent work">
            <p v-if="!batches && !analyses && (batchesError || analysesError)" class="px-4 py-6 text-sm text-muted">
              Couldn’t load the batches and analyses. Use Refresh to try again.
            </p>
            <DashboardRecentWork
              v-else
              :batches="batches ?? []"
              :analyses="analyses ?? []"
              :studies="studies"
              :loading="!batches && !analyses"
              :max-rows="workRows"
            />
          </BaseSection>
        </div>
      </div>
    </template>
  </div>
</template>
