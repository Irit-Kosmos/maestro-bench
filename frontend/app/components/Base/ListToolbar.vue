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

// The toolbar of a list: search, the Filter button, then the count and a refresh button on one row; the filters in use
// get a row of their own underneath, so adding one never reflows the controls.
// What is specific to a list goes in the slots: `default` after the Filter button, `trailing` and `group` (the Display menu) before the count.
const props = withDefaults(defineProps<{
  definitions: FilterDefinition[]
  /** Items before any search or filter, and how many are left */
  total: number
  shown: number
  /** Noun used in the count, e.g. "model" -> "12 models" */
  itemName?: string
  itemNamePlural?: string
  /** Shown instead of the search box when the list can't be searched */
  title?: string
  searchable?: boolean
  loading?: boolean
}>(), {
  itemName: undefined,
  itemNamePlural: undefined,
  title: undefined,
  searchable: true,
  loading: false,
})

const emit = defineEmits<{
  refresh: []
}>()

const search = defineModel<string>('search', { default: '' })
const filters = defineModel<FilterState>('filters', { required: true })

const searchInput = useTemplateRef<{ inputRef: HTMLInputElement | null }>('searchInput')
defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
})

const plural = computed(() => props.itemNamePlural ?? (props.itemName ? `${props.itemName}s` : undefined))

const countLabel = computed(() => {
  if (!props.itemName)
    return ''
  const noun = props.total === 1 ? props.itemName : plural.value
  return props.shown === props.total ? `${props.total} ${noun}` : `${props.shown} of ${props.total} ${noun}`
})
</script>

<template>
  <div class="flex min-h-11 shrink-0 flex-wrap items-center gap-x-1 gap-y-1 border-b border-default px-2 py-1">
    <UInput
      v-if="searchable"
      ref="searchInput"
      v-model="search"
      placeholder="Filter…"
      icon="i-ph-magnifying-glass-bold"
      size="sm"
      variant="none"
      :ui="{ base: 'focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted' }"
      :aria-label="`Filter ${plural ?? 'rows'}`"
      class="min-w-32 flex-1 sm:max-w-56"
      @keydown.esc="search = ''"
    >
      <template v-if="!search" #trailing>
        <BaseKbd value="/" />
      </template>
    </UInput>
    <h3 v-else-if="title" class="px-2 text-sm font-medium text-highlighted">
      {{ title }}
    </h3>

    <BaseFilterPicker v-if="definitions.length" v-model="filters" :definitions="definitions" />

    <slot />

    <span class="flex-1" />

    <slot name="trailing" />

    <slot name="group" />

    <span v-if="countLabel" class="ps-2 text-xs text-muted tabular-nums">{{ countLabel }}</span>
    <UTooltip text="Refresh">
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-arrows-clockwise-bold"
        size="sm"
        aria-label="Refresh"
        :loading="loading"
        @click="emit('refresh')"
      />
    </UTooltip>
  </div>

  <BaseFilterChips
    v-if="definitions.length"
    v-model="filters"
    :definitions="definitions"
    class="shrink-0 border-b border-default px-2 py-1.5"
  />
</template>
