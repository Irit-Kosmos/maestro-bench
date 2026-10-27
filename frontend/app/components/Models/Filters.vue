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
import type { FilterDefinition, FilterState } from '~/utils/filters'
import type { SortState } from '~/utils/sorts'
import { modelGroups, modelSorts } from '~/composables/useModelFilters'

// The toolbar of the models list: the shared one, with the same Display menu as the tables
defineProps<{
  definitions: FilterDefinition[]
  total: number
  shown: number
  loading?: boolean
}>()

const emit = defineEmits<{
  refresh: []
}>()

const search = defineModel<string>('search', { required: true })
const filters = defineModel<FilterState>('filters', { required: true })
const groupBy = defineModel<string | null>('groupBy', { required: true })
const sortBy = defineModel<SortState | null>('sortBy', { required: true })
</script>

<template>
  <BaseListToolbar
    v-model:search="search"
    v-model:filters="filters"
    :definitions="definitions"
    :total="total"
    :shown="shown"
    :loading="loading"
    item-name="model"
    @refresh="emit('refresh')"
  >
    <template #group>
      <BaseDisplayMenu v-model:group-by="groupBy" v-model:sort-by="sortBy" :groups="modelGroups" :sorts="modelSorts" />
    </template>
  </BaseListToolbar>
</template>
