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
import type { Analysis } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { SortSpec } from '~/utils/sorts'
import { authorFilter, dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'
import { dateSort, figureSort, nameSort } from '~/utils/sortSpecs'

definePageMeta({
  title: 'Analyses',
})

useSeoMeta({
  title: 'Analyses',
  description: 'Metrics such as RMSE, correlation or accuracy computed on experiment executions.',
})

const { data: analyses, pending, error, refresh } = await useMyLazyFetch<Analysis[]>('/analyses')

const { deleteAnalysis } = useAnalyses()
const { canEdit } = useCurrentWorkspace()
const { showDeleteSuccess, showDeleteError } = useStandardToast()

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
const analysisId = ref<number | null>(null)

const columns = [
  { key: 'name', label: 'Analysis' },
  {
    key: 'tags',
    label: 'Tags',
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, row: Analysis) => row.tags.map(tag => tag.name).join(' '),
  },
  {
    key: 'config',
    label: 'Ground truth vs prediction',
    formatter: (_: unknown, row: Analysis) =>
      `${row.config.truth_column} vs ${row.config.output_path || '(whole output)'}`,
  },
  {
    key: 'runs',
    label: 'Executions',
    formatter: (_: unknown, row: Analysis) => String(row.runs.length),
  },
  { key: 'updated_at', label: 'Updated' },
]

const filters: FilterSpec<Analysis>[] = [
  {
    key: 'value_type',
    label: 'Type',
    icon: 'i-ph-shapes-bold',
    value: analysis => analysis.config.value_type,
    present: value => value === 'numeric'
      ? { label: 'Numeric', icon: 'i-ph-hash-bold' }
      : { label: 'Categorical', icon: 'i-ph-tag-bold' },
  },
  {
    key: 'truth_column',
    label: 'Ground truth',
    icon: 'i-ph-columns-bold',
    plural: 'columns',
    searchPlaceholder: 'Search a column…',
    value: analysis => analysis.config.truth_column,
  },
  tagsFilter<Analysis>(analysis => analysis.tags),
  authorFilter(analysis => analysis.author),
  dateFilter(analysis => analysis.updated_at, 'Updated'),
]

const sorts: SortSpec<Analysis>[] = [
  nameSort(analysis => analysis.name, 'Analysis'),
  figureSort('runs', 'Executions', 'i-ph-repeat-bold', analysis => analysis.runs.length),
  dateSort(analysis => analysis.updated_at, 'Updated'),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})

const actions = [
  {
    label: 'Open',
    icon: 'i-ph-arrow-up-right-bold',
    handler: (analysis: Analysis) => navigateTo(`/analyses/${analysis.id}`),
  },
  {
    label: 'Delete',
    icon: 'i-ph-trash-bold',
    variant: 'ghost' as const,
    color: 'error' as const,
    requires: 'editor' as const,
    handler: (analysis: Analysis) => {
      analysisId.value = analysis.id
      showDeleteDialog.value = true
    },
  },
]

async function confirmDelete() {
  if (!analysisId.value)
    return
  isDeleting.value = true
  try {
    await deleteAnalysis(analysisId.value)
    showDeleteSuccess('Analysis')
    showDeleteDialog.value = false
    analysisId.value = null
    await refresh()
  }
  catch {
    showDeleteError('Analysis')
  }
  finally {
    isDeleting.value = false
  }
}
</script>

<template>
  <BasePageContent
    :loading="pending && !analyses"
    :error="!analyses && !!error"
    :error-kind="fetchErrorKind(error)"
    @retry="refresh()"
  >
    <template #before-content>
      <UTooltip text="New analysis" :kbds="['C']" :disabled="!canEdit">
        <UIGuardedButton
          color="neutral"
          variant="soft"
          icon="i-ph-plus-bold"
          size="sm"
          to="/analyses/new"
        >
          New analysis
        </UIGuardedButton>
      </UTooltip>
    </template>

    <div v-if="analyses && analyses.length > 0">
      <BaseDataTable
        v-model:filter-state="filterState"
        :data="[...(analyses || [])]"
        :columns="columns"
        :filters="filters"
        :sorts="sorts"
        :actions="actions"
        :loading="pending"
        :row-to="(analysis: Analysis) => `/analyses/${analysis.id}`"
        item-name="analysis"
        item-name-plural="analyses"
        searchable
        :selectable="canEdit"
        @refresh="refresh"
      >
        <template #selection-actions="{ rows }">
          <TagsBulkMenu kind="analysis" :rows="rows" @changed="refresh" />
          <StudiesBulkMenu kind="analysis" :ids="rows.map(row => row.id)" />
        </template>

        <template #tags-cell="{ row }">
          <TagsList :id="row.original.id" :tags="row.original.tags" :kind="canEdit ? 'analysis' : undefined" selectable @changed="refresh" @select="tag => { filterState = filterByTag(filterState, tag.name) }" />
        </template>

        <template #updated_at-cell="{ row }">
          <UIAuthorDate :date="row.original.updated_at" :person="row.original.author" />
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No analyses yet"
      message="Compare the outputs of one or more executions to a ground-truth column: RMSE, correlation, accuracy, kappa…"
      icon="i-ph-chart-bar-bold"
      action-label="New analysis"
      action-to="/analyses/new"
      action-requires="editor"
    />

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete analysis?"
      message="Executions and their results are kept. Only this comparison is removed."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="confirmDelete"
    />
  </BasePageContent>
</template>
