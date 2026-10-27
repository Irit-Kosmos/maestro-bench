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
import type { Tag } from '~/types'

// A tag: its colour as a dot, then its name. Removable in the field that edits tags.
// Small in tables and headers, medium where tags are edited. `selectable` makes it a button, e.g. to filter a list.
withDefaults(defineProps<{
  tag: Pick<Tag, 'name' | 'color'>
  removable?: boolean
  selectable?: boolean
  size?: 'sm' | 'md'
  // In a row that may be too narrow: the name is cut with an ellipsis instead of the chip overflowing
  shrinkable?: boolean
}>(), {
  size: 'sm',
})

const emit = defineEmits<{
  remove: []
  select: []
}>()
</script>

<template>
  <component
    :is="selectable ? 'button' : 'span'"
    :type="selectable ? 'button' : undefined"
    :title="selectable ? `Filter by ${tag.name}` : undefined"
    class="inline-flex items-center rounded-full border border-default bg-elevated/40 text-default"
    :class="[
      shrinkable ? 'min-w-0' : 'shrink-0',
      selectable ? 'cursor-pointer outline-none transition-colors duration-150 hover:bg-accented/50 focus-visible:ring-2 focus-visible:ring-inverted' : undefined,
      size === 'md' ? 'h-7 max-w-56 gap-2 ps-2.5 text-sm' : 'h-5 max-w-40 gap-1.5 ps-2 text-xs',
      removable ? 'pe-1' : size === 'md' ? 'pe-2.5' : 'pe-2',
    ]"
    @click="selectable && emit('select')"
  >
    <span class="shrink-0 rounded-full" :class="[tagDot(tag.color), size === 'md' ? 'size-2.5' : 'size-2']" aria-hidden="true" />
    <span class="min-w-0 truncate" :title="selectable ? undefined : tag.name">{{ tag.name }}</span>
    <button
      v-if="removable"
      type="button"
      :aria-label="`Remove tag ${tag.name}`"
      class="flex shrink-0 cursor-pointer items-center justify-center rounded-full text-muted outline-none transition-colors duration-150 hover:bg-accented/60 hover:text-default focus-visible:bg-accented/60 focus-visible:text-default focus-visible:ring-2 focus-visible:ring-inverted"
      :class="size === 'md' ? 'size-5' : 'size-4'"
      @click="emit('remove')"
    >
      <UIcon name="i-ph-x-bold" :class="size === 'md' ? 'size-3.5' : 'size-3'" aria-hidden="true" />
    </button>
  </component>
</template>
