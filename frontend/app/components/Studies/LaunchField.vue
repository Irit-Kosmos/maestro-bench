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
import type { Study } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

defineProps<{
  /** Without its label, under a title edited in place: the button says what it is */
  bare?: boolean
}>()

// The studies a new experiment or batch is put in once it starts. Nothing is saved here: the page does it
// when it launches, so leaving the form leaves the studies as they were (except one made from this field).
const model = defineModel<number[]>({ default: () => [] })

const { studies, createStudy } = useStudies()
const { fail } = useStandardToast()

const chosen = computed(() => model.value
  .map(id => studies.value.find(study => study.id === id))
  .filter((study): study is Study => !!study))

const open = ref(false)
const creating = ref(false)

function toggle(study: Study) {
  model.value = model.value.includes(study.id)
    ? model.value.filter(id => id !== study.id)
    : [...model.value, study.id]
}

async function create(name: string) {
  creating.value = true
  try {
    const study = await createStudy({ name })
    model.value = [...model.value, study.id]
  }
  catch (error) {
    fail('Couldn’t create the study', apiErrorMessage(error))
  }
  finally {
    creating.value = false
  }
}
</script>

<template>
  <UFormField :label="bare ? undefined : 'Studies'" :hint="bare ? undefined : 'Optional'">
    <div class="flex flex-wrap items-center gap-1.5">
      <span
        v-for="study in chosen"
        :key="study.id"
        class="inline-flex h-7 max-w-56 items-center gap-1.5 rounded-md border border-default ps-2 pe-1 text-sm text-toned"
      >
        <StudiesStatusIcon :status="study.status" />
        <span class="truncate" :title="study.name">{{ study.name }}</span>
        <button
          type="button"
          :aria-label="`Remove from ${study.name}`"
          class="flex size-5 cursor-pointer items-center justify-center rounded text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default focus-visible:ring-2 focus-visible:ring-inverted"
          @click="toggle(study)"
        >
          <UIcon name="i-ph-x-bold" class="size-3" aria-hidden="true" />
        </button>
      </span>

      <UPopover v-model:open="open" :content="{ align: 'start', sideOffset: 6, collisionPadding: 16 }" :ui="{ content: 'overflow-hidden' }">
        <button
          type="button"
          class="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-accented px-2 text-sm text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default focus-visible:ring-2 focus-visible:ring-inverted data-[state=open]:bg-elevated data-[state=open]:text-default"
        >
          <UIcon name="i-ph-plus-bold" class="size-3.5" aria-hidden="true" />
          {{ chosen.length ? 'Add to another study' : 'Add to a study' }}
        </button>

        <template #content>
          <StudiesPicker :selected="model" :creating="creating" active-only @toggle="toggle" @create="create" />
        </template>
      </UPopover>
    </div>
  </UFormField>
</template>
