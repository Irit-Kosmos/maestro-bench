<script setup lang="ts">
import type { Analysis } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'

definePageMeta({
  title: 'Analyses',
  subtitle: 'Compare executions against a ground-truth column',
})

useSeoMeta({
  title: 'Analyses',
  description: 'Metrics such as RMSE, correlation or accuracy computed on experiment executions.',
})

const { data: analyses, pending, refresh } = await useMyLazyFetch<Analysis[]>('/analyses')

const { deleteAnalysis } = useAnalyses()
const { formatDate, formatRelativeDate } = useUIHelpers()
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
    icon: 'i-lucide-shapes',
    value: analysis => analysis.config.value_type,
    present: value => value === 'numeric'
      ? { label: 'Numeric', icon: 'i-lucide-hash' }
      : { label: 'Categorical', icon: 'i-lucide-tags' },
  },
  {
    key: 'truth_column',
    label: 'Ground truth',
    icon: 'i-lucide-columns-3',
    plural: 'columns',
    searchPlaceholder: 'Search a column…',
    value: analysis => analysis.config.truth_column,
  },
  tagsFilter<Analysis>(analysis => analysis.tags),
  dateFilter(analysis => analysis.updated_at, 'Updated'),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})

const actions = [
  {
    label: 'Open',
    icon: 'i-lucide-arrow-up-right',
    handler: (analysis: Analysis) => navigateTo(`/analyses/${analysis.id}`),
  },
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
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
  <BasePageContent :loading="pending && !analyses">
    <template #before-content>
      <UTooltip text="New analysis" :kbds="['C']">
        <UButton
          color="neutral"
          variant="soft"
          icon="i-lucide-plus"
          size="sm"
          to="/analyses/new"
        >
          New analysis
        </UButton>
      </UTooltip>
    </template>

    <div v-if="analyses && analyses.length > 0">
      <BaseDataTable
        v-model:filter-state="filterState"
        :data="[...(analyses || [])]"
        :columns="columns"
        :filters="filters"
        :actions="actions"
        :loading="pending"
        :row-to="(analysis: Analysis) => `/analyses/${analysis.id}`"
        item-name="analysis"
        item-name-plural="analyses"
        searchable
        selectable
        @refresh="refresh"
      >
        <template #selection-actions="{ rows }">
          <TagsBulkMenu kind="analysis" :rows="rows" @changed="refresh" />
        </template>

        <template #tags-cell="{ row }">
          <TagsList :tags="row.original.tags" selectable @select="tag => { filterState = filterByTag(filterState, tag.name) }" />
        </template>

        <template #updated_at-cell="{ row }">
          <span class="text-sm text-muted tabular-nums" :title="formatDate(row.original.updated_at)">
            {{ formatRelativeDate(row.original.updated_at) }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <BaseEmptyState
      v-else-if="!pending"
      title="No analyses yet"
      message="Compare the outputs of one or more executions to a ground-truth column: RMSE, correlation, accuracy, kappa…"
      icon="i-lucide-chart-column"
      action-label="New analysis"
      action-to="/analyses/new"
    />

    <UModal v-model:open="showDeleteDialog" title="Delete analysis?">
      <template #body>
        <p class="text-sm text-toned">
          Executions and their results are kept. Only this comparison is removed.
        </p>
      </template>
      <template #footer>
        <div class="flex gap-3 w-full justify-end">
          <UButton variant="outline" color="neutral" @click="() => { showDeleteDialog = false }">
            Cancel
          </UButton>
          <UButton variant="solid" color="error" :loading="isDeleting" @click="confirmDelete">
            Delete analysis
          </UButton>
        </div>
      </template>
    </UModal>
  </BasePageContent>
</template>
