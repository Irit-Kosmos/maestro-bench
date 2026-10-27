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
import type { FilterDefinition, FilterMode, FilterOption, FilterState } from '~/utils/filters'
import { effectiveMode, filterModes, modeLabel } from '~/utils/filters'

// The filters in use, one chip each, on their own row under the toolbar (hidden when there are none).
// Chips wrap onto more lines rather than pushing the toolbar around; "+" adds another, Clear drops them all.
const props = defineProps<{
  definitions: FilterDefinition[]
}>()
const filters = defineModel<FilterState>({ required: true })

const { entryFor, selectedFor, toggle, setMode, remove, clearAll, activeDefinitions } = useFilterEditing(filters, () => props.definitions)

function selectedOptions(definition: FilterDefinition): FilterOption[] {
  const selected = selectedFor(definition.key)
  return definition.options.filter(option => selected.includes(option.value))
}

function operator(definition: FilterDefinition) {
  const entry = entryFor(definition.key)
  return modeLabel(effectiveMode(entry), entry.values.length)
}

// "is all of" only differs from "is any of" once two values are picked, so it is offered from then on
function modeOptions(definition: FilterDefinition): FilterOption[] {
  const count = selectedFor(definition.key).length
  return filterModes(definition)
    .filter(mode => mode !== 'all' || count > 1)
    .map(mode => ({ value: mode, label: modeLabel(mode, count) }))
}

// Two short labels read fine side by side ("Active, Inactive"); past that, a count is clearer
function valueLabel(definition: FilterDefinition) {
  const labels = selectedOptions(definition).map(option => option.label)
  if (labels.length === 1 || (labels.length === 2 && labels.join(', ').length <= 14))
    return labels.join(', ')
  return `${labels.length} ${definition.plural ?? 'values'}`
}

// Past three icons (or dots), the rest collapse into an ellipsis
const CHIP_ICON_LIMIT = 3
const iconOptions = (definition: FilterDefinition) => selectedOptions(definition).filter(option => option.icon || option.dot)
const chipIcons = (definition: FilterDefinition) => iconOptions(definition).slice(0, CHIP_ICON_LIMIT)
const hasMoreIcons = (definition: FilterDefinition) => iconOptions(definition).length > CHIP_ICON_LIMIT

const POPOVER_CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
const SEGMENT = 'inline-flex cursor-pointer items-center gap-1.5 rounded-sm px-1.5 transition-colors duration-150 ease-out hover:bg-accented/60 data-[state=open]:bg-accented/60'
</script>

<template>
  <div v-if="activeDefinitions.length" class="flex flex-wrap items-center gap-1">
    <div
      v-for="definition in activeDefinitions"
      :key="definition.key"
      class="inline-flex h-7 shrink-0 items-stretch gap-0.5 rounded-md bg-elevated p-0.5 text-xs whitespace-nowrap"
    >
      <!-- What is filtered, and how -->
      <span class="inline-flex items-center gap-1.5 ps-1.5 text-muted">
        <UIcon :name="definition.icon" class="size-3.5" aria-hidden="true" />
        {{ definition.label }}
      </span>
      <UPopover v-if="modeOptions(definition).length > 1" :content="POPOVER_CONTENT">
        <button
          type="button"
          class="font-semibold text-muted hover:text-highlighted data-[state=open]:text-highlighted"
          :class="SEGMENT"
          :aria-label="`${operator(definition)}, change ${definition.label} operator`"
        >
          {{ operator(definition) }}
          <UIcon name="i-ph-caret-down-bold" class="size-3" aria-hidden="true" />
        </button>
        <template #content>
          <BaseFilterOptionList
            class="w-36"
            :options="modeOptions(definition)"
            :selected="[effectiveMode(entryFor(definition.key))]"
            @toggle="setMode(definition, $event as FilterMode)"
          />
        </template>
      </UPopover>
      <span v-else class="inline-flex items-center px-1.5 font-semibold text-muted">{{ operator(definition) }}</span>
      <span class="my-1 w-px bg-accented" aria-hidden="true" />
      <UPopover :content="POPOVER_CONTENT">
        <button
          type="button"
          class="font-medium text-highlighted"
          :class="SEGMENT"
          :aria-label="`${valueLabel(definition)}, change ${definition.label} filter`"
        >
          <!-- Each icon sits on top of the one to its left, cut out by a ring in the chip's own colour -->
          <span v-if="chipIcons(definition).length" class="inline-flex items-center -space-x-1">
            <span
              v-for="option in chipIcons(definition)"
              :key="String(option.value)"
              class="relative inline-flex size-4 items-center justify-center rounded-full bg-elevated ring-(--ui-bg-elevated)"
              :class="option.icon ? 'ring-2' : 'ring-1'"
            >
              <UIcon v-if="option.icon" :name="option.icon" class="size-3.5" :class="option.iconClass" aria-hidden="true" />
              <span v-else class="size-3 rounded-full" :class="option.dot" aria-hidden="true" />
            </span>
            <span
              v-if="hasMoreIcons(definition)"
              class="relative inline-flex size-4 items-center justify-center rounded-full bg-elevated text-muted ring-2 ring-(--ui-bg-elevated)"
              aria-hidden="true"
            >
              <UIcon name="i-ph-dots-three-bold" class="size-3.5" />
            </span>
          </span>
          {{ valueLabel(definition) }}
          <UIcon name="i-ph-caret-down-bold" class="size-3 text-dimmed" aria-hidden="true" />
        </button>
        <template #content>
          <BaseFilterOptionList
            class="w-48"
            :options="definition.options"
            :selected="selectedFor(definition.key)"
            :multiple="definition.multiple"
            :search-placeholder="definition.searchPlaceholder"
            @toggle="toggle(definition, $event)"
          />
        </template>
      </UPopover>
      <span class="my-1 w-px bg-accented" aria-hidden="true" />
      <button
        type="button"
        class="inline-flex cursor-pointer items-center rounded-sm px-1.5 text-muted transition-colors duration-150 ease-out hover:bg-accented/60 hover:text-highlighted"
        :aria-label="`Remove ${definition.label} filter`"
        @click="remove(definition)"
      >
        <UIcon name="i-ph-x-bold" class="size-3.5" />
      </button>
    </div>

    <BaseFilterPicker v-model="filters" :definitions="definitions" compact />

    <UButton
      color="neutral"
      variant="ghost"
      size="xs"
      label="Clear"
      class="ms-auto text-muted"
      @click="clearAll"
    />
  </div>
</template>
