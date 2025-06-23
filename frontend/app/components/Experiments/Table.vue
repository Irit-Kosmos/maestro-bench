<script setup lang="ts">
import type { Experiment } from '~/types'

interface Props {
  experiments: Experiment[]
  loading?: boolean
  actionTo?: string
}

interface Emits {
  refresh: []
  viewExperiment: [id: number]
  deleteExperiment: [id: number]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { getStatusColor, formatDate } = useUIHelpers()

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Experiment',
  },
  {
    key: 'dataset',
    label: 'Dataset',
  },
  {
    key: 'status',
    label: 'Status',
  },
  {
    key: 'created_at',
    label: 'Created',
  },
]

const actions = [
  {
    label: 'View',
    icon: 'i-lucide-eye',
    variant: 'ghost' as const,
    color: 'neutral' as const,
    handler: (experiment: Experiment) => handleViewExperiment(experiment.id),
  },
]

function handleViewExperiment(id: number) {
  emit('viewExperiment', id)
}

function handleRefresh() {
  emit('refresh')
}
</script>

<template>
  <BaseDataTable
    :data="experiments"
    :columns="columns"
    :actions="actions"
    :loading="loading"
    :action-to="props.actionTo"
    title="Recent Experiments"
    empty-message="Get started by creating your first experiment."
    @refresh="handleRefresh"
  >
    <!-- Custom cell for name (with ID) -->
    <template #name-cell="{ row }">
      <div>
        <div class="text-sm font-medium text-neutral-900">
          {{ row.original.name }}
        </div>
        <div class="text-sm text-neutral-500">
          ID: {{ row.original.id }}
        </div>
      </div>
    </template>

    <!-- Custom cell for dataset -->
    <template #dataset-cell="{ row }">
      <div>
        <div class="text-sm text-neutral-900">
          {{ row.original.dataset?.name || 'Unknown' }}
        </div>
        <div class="text-sm text-neutral-500">
          {{ row.original.dataset?.description || '' }}
        </div>
      </div>
    </template>

    <!-- Custom cell for status -->
    <template #status-cell="{ row }">
      <UBadge
        :color="getStatusColor(row.original.status || 'pending')"
        variant="soft"
      >
        {{ row.original.status || 'pending' }}
      </UBadge>
    </template>

    <!-- Custom cell for created_at -->
    <template #created_at-cell="{ row }">
      <span class="text-sm text-neutral-500">
        {{ formatDate(row.original.created_at) }}
      </span>
    </template>
  </BaseDataTable>
</template>
