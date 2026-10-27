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
import { apiErrorMessage } from '~/composables/useAnalyses'

// The tags of the selected rows of a list. A tag every row has is checked, one only some have is dashed;
// clicking it puts it on every row, or takes it off every row when they all have it already.
// The default slot is the button that opens it: "Tags" in a selection bar, a small "+" on a row (see TagsList).
const props = defineProps<{
  kind: 'prompt' | 'analysis' | 'agent' | 'study'
  rows: { id: number, tags: Tag[] }[]
}>()

const emit = defineEmits<{
  /** The tags of the rows changed: the list should be read again */
  changed: []
}>()

const { assignTags } = useTags()
const { fail } = useStandardToast()

const coverage = computed(() => tagCoverage(props.rows))
function ids(everyRow: boolean) {
  return [...coverage.value]
    .filter(([, count]) => everyRow ? count === props.rows.length : count < props.rows.length)
    .map(([id]) => id)
}
const onEvery = computed(() => ids(true))
const onSome = computed(() => ids(false))

async function apply(change: { add?: number[], remove?: number[] }) {
  try {
    await assignTags(props.kind, props.rows.map(row => row.id), change)
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t update the tags', apiErrorMessage(error))
  }
}

function toggle(tag: Tag) {
  return apply(onEvery.value.includes(tag.id) ? { remove: [tag.id] } : { add: [tag.id] })
}

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <UPopover :content="CONTENT" :ui="{ content: 'overflow-hidden' }">
    <slot>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-tag-bold"
        size="sm"
      >
        Tags
      </UButton>
    </slot>

    <template #content>
      <TagsPicker
        :selected="onEvery"
        :partial="onSome"
        @toggle="toggle"
        @create="tag => apply({ add: [tag.id] })"
      />
    </template>
  </UPopover>
</template>
