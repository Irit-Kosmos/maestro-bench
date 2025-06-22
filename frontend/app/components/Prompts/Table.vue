<script setup lang="ts">
import type { Prompt } from '~/types'

interface Props {
  data: Prompt[]
  loading?: boolean
}

defineProps<Props>()

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Prompt Name',
  },
  {
    key: 'category',
    label: 'Category',
  },
  {
    key: 'description',
    label: 'Description',
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
    handler: (prompt: Prompt) => handleViewPrompt(prompt.id),
  },
]

// Methods
async function handleViewPrompt(id: number) {
  await navigateTo(`/prompts/${id}`)
}
</script>

<template>
  <BaseDataTable
    :data="data"
    :columns="columns"
    :actions="actions"
    :loading="loading"
    title="All Prompts"
    searchable
  >
    <!-- Custom cell for category -->
    <template #category-cell="{ row }">
      <UBadge
        v-if="row.original.category"
        color="neutral"
        variant="soft"
      >
        {{ row.original.category }}
      </UBadge>
      <span v-else class="text-neutral-400 text-sm">
        No category
      </span>
    </template>

    <!-- Custom cell for created_at -->
    <template #created_at-cell="{ row }">
      <span class="text-sm text-neutral-500">
        {{ new Date(row.original.created_at).toLocaleDateString() }}
      </span>
    </template>

    <!-- Custom cell for description -->
    <template #description-cell="{ row }">
      <span class="text-sm text-neutral-600">
        {{ row.original.description || 'No description' }}
      </span>
    </template>
  </BaseDataTable>
</template>
