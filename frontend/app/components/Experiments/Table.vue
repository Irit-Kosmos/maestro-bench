<script setup lang="ts">
import type { TableColumn } from '@nuxt/ui'
import type { Experiment } from '~/types'
import { h, resolveComponent } from 'vue'

interface Props {
  experiments: Experiment[]
  loading?: boolean
}

interface Emits {
  refresh: []
  viewExperiment: [id: number]
  deleteExperiment: [id: number]
}

defineProps<Props>()
const emit = defineEmits<Emits>()

const { getStatusColor, formatDate } = useUIHelpers()

const UButton = resolveComponent('UButton')
const UBadge = resolveComponent('UBadge')
const UIcon = resolveComponent('UIcon')

function handleViewExperiment(id: number) {
  emit('viewExperiment', id)
}

function handleRefresh() {
  emit('refresh')
}

const columns: TableColumn<Experiment>[] = [
  {
    accessorKey: 'name',
    header: 'Experiment',
    cell: ({ row }) => {
      const experiment = row.original
      return h('div', {}, [
        h('div', { class: 'text-sm font-medium text-gray-900' }, experiment.name),
        h('div', { class: 'text-sm text-gray-500' }, `ID: ${experiment.id}`),
      ])
    },
  },
  {
    accessorKey: 'dataset',
    header: 'Dataset',
    cell: ({ row }) => {
      const dataset = row.original.dataset
      return h('div', {}, [
        h('div', { class: 'text-sm text-gray-900' }, dataset?.name || 'Unknown'),
        h('div', { class: 'text-sm text-gray-500' }, dataset?.description || ''),
      ])
    },
  },
  {
    accessorKey: 'status',
    header: 'Status',
    cell: ({ row }) => {
      const status = row.original.status || 'pending'
      return h(UBadge, {
        color: getStatusColor(status),
        variant: 'soft',
      }, () => status)
    },
  },
  {
    accessorKey: 'results',
    header: 'Results',
    cell: ({ row }) => {
      const results = row.original.results
      if (results && results.total_questions) {
        return h('div', { class: 'text-sm text-gray-500' }, `${results.total_questions} questions`)
      }
      return h('span', { class: 'text-sm text-gray-400' }, 'No results yet')
    },
  },
  {
    accessorKey: 'created_at',
    header: 'Created',
    cell: ({ row }) => {
      return h('span', { class: 'text-sm text-gray-500' }, formatDate(row.original.created_at))
    },
  },
  {
    id: 'actions',
    header: 'Actions',
    cell: ({ row }) => {
      return h(
        'div',
        { class: 'flex items-center gap-2' },
        [
          h(UButton, {
            variant: 'ghost',
            size: 'sm',
            icon: 'i-lucide-eye',
            onClick: () => handleViewExperiment(row.original.id),
          }),
        ],
      )
    },
  },
]
</script>

<template>
  <div class="bg-white rounded-lg shadow">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex justify-between items-center">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">
            Recent Experiments
          </h2>
        </div>
        <UButton
          variant="ghost"
          size="sm"
          icon="i-lucide:refresh-cw"
          :loading="loading"
          @click="handleRefresh"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <div class="overflow-hidden">
      <!-- Empty State -->
      <div v-if="!experiments || experiments.length === 0" class="p-12 text-center">
        <UIcon name="i-lucide:flask" class="mx-auto h-12 w-12 text-gray-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          No experiments yet
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          Get started by creating your first experiment.
        </p>
      </div>

      <!-- Experiments UTable -->
      <UTable
        v-else
        :data="experiments"
        :columns="columns"
        :loading="loading"
        class="min-w-full"
        :ui="{
          th: 'px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider',
          td: 'px-6 py-4 whitespace-nowrap',
          tbody: 'bg-white divide-y divide-gray-200 [&>tr]:hover:bg-gray-50',
        }"
      />
    </div>
  </div>
</template>
