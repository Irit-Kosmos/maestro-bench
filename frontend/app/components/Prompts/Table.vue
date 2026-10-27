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
import type { Prompt } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { SortSpec } from '~/utils/sorts'
import { dateFilter, filterByTag, tagsFilter } from '~/utils/filterSpecs'
import { dateSort, nameSort, textSort } from '~/utils/sortSpecs'

interface Props {
  data: Prompt[]
  loading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  refresh: []
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()
const { canEdit } = useCurrentWorkspace()

// Table configuration
const columns = [
  {
    key: 'name',
    label: 'Prompt',
  },
  {
    key: 'tags',
    label: 'Tags',
    // What the search reads; the cell below shows the chips
    formatter: (_: unknown, prompt: Prompt) => prompt.tags.map(tag => tag.name).join(' '),
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

const filters: FilterSpec<Prompt>[] = [
  tagsFilter<Prompt>(prompt => prompt.tags),
  dateFilter(prompt => prompt.created_at),
]

const sorts: SortSpec<Prompt>[] = [
  nameSort(prompt => prompt.name, 'Prompt'),
  textSort('description', 'Description', 'i-ph-text-align-left-bold', prompt => prompt.description),
  dateSort(prompt => prompt.created_at),
]

// Clicking a tag in a row filters the list on it
const filterState = ref<FilterState>({})
</script>

<template>
  <BaseDataTable
    v-model:filter-state="filterState"
    :data="data"
    :columns="columns"
    :filters="filters"
    :sorts="sorts"
    :loading="loading"
    :row-to="(prompt: Prompt) => `/prompts/${prompt.id}`"
    item-name="prompt"
    searchable
    :selectable="canEdit"
    @refresh="emit('refresh')"
  >
    <template #selection-actions="{ rows }">
      <TagsBulkMenu kind="prompt" :rows="rows" @changed="emit('refresh')" />
    </template>

    <template #tags-cell="{ row }">
      <TagsList :id="row.original.id" :tags="row.original.tags" kind="prompt" selectable @changed="emit('refresh')" @select="tag => { filterState = filterByTag(filterState, tag.name) }" />
    </template>

    <!-- Custom cell for created_at -->
    <template #created_at-cell="{ row }">
      <span class="text-sm text-muted" :title="formatDate(row.original.created_at)">
        {{ formatRelativeDate(row.original.created_at) }}
      </span>
    </template>

    <!-- Custom cell for description -->
    <template #description-cell="{ row }">
      <span class="block max-w-md truncate text-sm text-toned" :title="row.original.description || undefined">
        {{ row.original.description || '—' }}
      </span>
    </template>
  </BaseDataTable>
</template>
