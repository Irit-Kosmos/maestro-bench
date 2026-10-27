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
  id: number
}>()

const { studies, assignStudies } = useStudies()
const { fail } = useStandardToast()
const { memberships, refreshMemberships } = useStudyMemberships(() => props.kind)
const { canEdit } = useCurrentWorkspace()

const mine = computed(() => {
  const ids = new Set(memberships.value.filter(m => m.item_id === props.id).map(m => m.study_id))
  return studies.value.filter(study => ids.has(study.id))
})

// An archived study is read-only: the item stays in it
function removable(study: Study) {
  return canEdit.value && study.status !== 'archived'
}

async function remove(study: Study) {
  try {
    await assignStudies(props.kind, [props.id], { remove: [study.id] })
    await refreshMemberships()
  }
  catch (error) {
    fail('Couldn’t remove from the study', apiErrorMessage(error))
  }
}
</script>

<template>
  <div v-if="mine.length || canEdit" class="flex flex-wrap items-center gap-1.5">
    <span
      v-for="study in mine"
      :key="study.id"
      class="inline-flex h-6 max-w-56 items-center rounded-md border border-default text-xs text-toned transition-colors hover:bg-elevated"
    >
      <NuxtLink
        :to="`/studies/${study.id}`"
        class="inline-flex min-w-0 items-center gap-1.5 rounded-s-md ps-2 text-toned outline-none transition-colors hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
        :class="removable(study) ? 'pe-1' : 'rounded-e-md pe-2'"
      >
        <StudiesStatusIcon :status="study.status" />
        <span class="truncate">{{ study.name }}</span>
      </NuxtLink>
      <button
        v-if="removable(study)"
        type="button"
        class="me-0.5 inline-flex size-5 shrink-0 cursor-pointer items-center justify-center rounded text-muted outline-none transition-colors hover:bg-accented hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
        :aria-label="`Remove from ${study.name}`"
        data-tooltip="Remove from this study"
        @click="remove(study)"
      >
        <UIcon name="i-ph-x-bold" class="size-3" aria-hidden="true" />
      </button>
    </span>

    <StudiesBulkMenu v-if="canEdit" :kind="kind" :ids="[id]" @changed="refreshMemberships">
      <button
        type="button"
        class="inline-flex h-6 cursor-pointer items-center gap-1 rounded-md border border-dashed border-accented px-2 text-xs text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default focus-visible:ring-2 focus-visible:ring-inverted data-[state=open]:bg-elevated data-[state=open]:text-default"
      >
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
        {{ mine.length ? 'Add to another study' : 'Add to a study' }}
      </button>
    </StudiesBulkMenu>
  </div>
</template>
