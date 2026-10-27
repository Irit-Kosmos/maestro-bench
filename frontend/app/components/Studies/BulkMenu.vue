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
import type { Study, StudyKind } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  kind: StudyKind
  /** Ids of the selected items */
  ids: number[]
}>()

const emit = defineEmits<{
  /** The studies of the items changed */
  changed: []
}>()

const { createStudy, assignStudies, refreshStudies } = useStudies()
const { memberships, refreshMemberships } = useStudyMemberships(() => props.kind)
const { ok, fail } = useStandardToast()

const coverage = computed(() => studyCoverage(memberships.value, props.ids))
function studyIds(everyItem: boolean) {
  return [...coverage.value]
    .filter(([, count]) => everyItem ? count === props.ids.length : count < props.ids.length)
    .map(([id]) => id)
}
const onEvery = computed(() => studyIds(true))
const onSome = computed(() => studyIds(false))

const creating = ref(false)

async function apply(change: { add?: number[], remove?: number[] }) {
  try {
    await assignStudies(props.kind, props.ids, change)
    await refreshMemberships()
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t update the studies', apiErrorMessage(error))
  }
}

function toggle(study: Study) {
  return apply(onEvery.value.includes(study.id) ? { remove: [study.id] } : { add: [study.id] })
}

// A study made here starts with the selection in it
async function create(name: string) {
  creating.value = true
  try {
    const study = await createStudy({ name, items: props.ids.map(item_id => ({ kind: props.kind, item_id })) })
    await refreshMemberships()
    ok('Study created', { description: `“${study.name}” holds the selection.`, action: { label: 'Open', to: `/studies/${study.id}` } })
    emit('changed')
  }
  catch (error) {
    fail('Couldn’t create the study', apiErrorMessage(error))
  }
  finally {
    creating.value = false
  }
}

function onOpen(open: boolean) {
  if (open) {
    refreshStudies()
    refreshMemberships()
  }
}

const CONTENT = { align: 'start', sideOffset: 6, collisionPadding: 16 } as const
</script>

<template>
  <UPopover :content="CONTENT" :ui="{ content: 'overflow-hidden' }" @update:open="onOpen">
    <slot>
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-notebook-bold"
        size="sm"
      >
        Studies
      </UButton>
    </slot>

    <template #content>
      <StudiesPicker
        :selected="onEvery"
        :partial="onSome"
        :creating="creating"
        @toggle="toggle"
        @create="create"
      />
    </template>
  </UPopover>
</template>
