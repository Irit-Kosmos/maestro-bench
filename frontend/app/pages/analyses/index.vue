<script setup lang="ts">
import type { Analysis } from '~/types'

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
  <BasePageContent :loading="pending">
    <template #before-content>
      <UTooltip text="New analysis" :kbds="['C']">
        <UButton
          color="primary"
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
        :data="[...(analyses || [])]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        :row-to="(analysis: Analysis) => `/analyses/${analysis.id}`"
        item-name="analysis"
        item-name-plural="analyses"
        searchable
        @refresh="refresh"
      >
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
