<script setup lang="ts">
import type { Experiment } from '~/types'

// Composables
const { experiments, pending, refresh } = useExperiments()
const toast = useToast()

// Page meta
useSeoMeta({
  title: 'Experiments',
  description: 'Manage and monitor your AI agent experiments. Create, view, and analyze experiment results.',
})

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Experiment',
    formatter: (value: string, row: Experiment) => `${value} (ID: ${row.id})`,
  },
  {
    key: 'dataset',
    label: 'Dataset',
    formatter: (_: any, row: Experiment) => row.dataset?.name || 'Unknown',
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
  {
    label: 'Delete',
    icon: 'i-lucide-trash-2',
    variant: 'ghost' as const,
    color: 'error' as const,
    handler: (experiment: Experiment) => handleDeleteExperiment(experiment.id),
  },
]

// Navigation handlers
async function handleViewExperiment(id: number) {
  await navigateTo(`/experiments/${id}`)
}

async function handleDeleteExperiment(_id: number) {
  // TODO: Add confirmation dialog
  toast.add({
    title: 'Coming Soon',
    description: 'Delete confirmation dialog coming soon!',
    color: 'info',
    icon: 'i-lucide:info',
  })
}

async function handleCreateExperiment() {
  await navigateTo('/experiments/new')
}
</script>

<template>
  <BasePageLayout
    title="Experiments"
    subtitle="Manage and monitor your experiments"
    :loading="pending"
  >
    <template #actions>
      <UButton
        variant="solid"
        color="primary"
        icon="i-lucide:plus"
        size="lg"
        @click="handleCreateExperiment"
      >
        Create Experiment
      </UButton>
    </template>

    <!-- Experiments Table -->
    <div v-if="experiments && experiments.length > 0">
      <BaseDataTable
        :data="[...(experiments || [])]"
        :columns="columns"
        :actions="actions"
        :loading="pending"
        title="All Experiments"
        searchable
        @refresh="refresh"
      >
        <!-- Custom cell for status -->
        <template #cell-status="{ item }">
          <UIStatusBadge :status="item.status" />
        </template>

        <!-- Custom cell for created_at -->
        <template #cell-created_at="{ item }">
          <span class="text-sm text-neutral-500">
            {{ new Date(item.created_at).toLocaleDateString() }}
          </span>
        </template>
      </BaseDataTable>
    </div>

    <!-- Empty State -->
    <BaseEmptyState
      v-else-if="!pending"
      title="No experiments yet"
      message="Get started by creating your first experiment to test your agent teams."
      icon="i-lucide:flask-conical"
      action-label="Create Your First Experiment"
      @action="handleCreateExperiment"
    />
  </BasePageLayout>
</template>
