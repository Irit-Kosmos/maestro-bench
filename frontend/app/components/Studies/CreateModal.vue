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
import type { StudyDetail } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const emit = defineEmits<{
  created: [study: StudyDetail]
}>()

const open = defineModel<boolean>('open', { default: false })

const { createStudy } = useStudies()
const { showCreateSuccess, showCreateError } = useStandardToast()

const name = ref('')
const isCreating = ref(false)
const valid = computed(() => name.value.trim().length > 0)

async function submit() {
  if (!valid.value)
    return
  isCreating.value = true
  try {
    const study = await createStudy({ name: name.value.trim() })
    showCreateSuccess('Study')
    open.value = false
    emit('created', study)
  }
  catch (error) {
    showCreateError('Study', apiErrorMessage(error))
  }
  finally {
    isCreating.value = false
  }
}
</script>

<template>
  <BaseCrudModal
    v-model:open="open"
    title="Study"
    mode="create"
    :loading="isCreating"
    :disabled="!valid"
    @submit="submit"
    @after-leave="name = ''"
  >
    <UFormField label="Name" required help="A theme to gather experiments, batches and analyses around, e.g. “Does prompt v3 beat v2?”">
      <UInput v-model="name" class="w-full" autofocus maxlength="200" placeholder="Study name" />
    </UFormField>
  </BaseCrudModal>
</template>
