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
import type { Dataset } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  /** The dataset being edited; the form takes its values each time the dialog opens */
  dataset: Dataset | null
}>()

const emit = defineEmits<{
  saved: [dataset: Dataset]
}>()

const open = defineModel<boolean>('open', { default: false })

const { updateDataset } = useDatasets()
const { showUpdateSuccess, showUpdateError } = useStandardToast()

const name = ref('')
const description = ref('')
const saving = ref(false)

// The form starts from what the dataset holds now, not from what it held the last time
watch(open, (isOpen) => {
  if (isOpen) {
    name.value = props.dataset?.name ?? ''
    description.value = props.dataset?.description ?? ''
  }
})

const changed = computed(() =>
  name.value.trim() !== props.dataset?.name
  || description.value.trim() !== (props.dataset?.description ?? ''),
)
const valid = computed(() => name.value.trim().length > 0 && changed.value)

async function submit() {
  if (!props.dataset || !valid.value || saving.value)
    return

  saving.value = true
  try {
    const dataset = await updateDataset(props.dataset.id, {
      name: name.value.trim(),
      description: description.value.trim() || null,
    })
    showUpdateSuccess('Dataset')
    open.value = false
    emit('saved', dataset)
  }
  catch (error) {
    showUpdateError('Dataset', apiErrorMessage(error))
  }
  finally {
    saving.value = false
  }
}
</script>

<template>
  <UModal
    v-model:open="open"
    title="Edit dataset"
    description="Change the name and description of this dataset."
    :dismissible="!saving"
  >
    <template #content>
      <UCard>
        <template #header>
          <h2 class="text-base font-semibold text-highlighted">
            Edit dataset
          </h2>
        </template>

        <form class="space-y-4" @submit.prevent="submit">
          <UFormField label="Name" required>
            <UInput v-model="name" class="w-full" maxlength="200" autofocus />
          </UFormField>

          <UFormField label="Description">
            <UTextarea
              v-model="description"
              class="w-full"
              placeholder="What the rows are, where they come from"
              :rows="3"
              maxlength="2000"
              @keydown.meta.enter.prevent="submit"
              @keydown.ctrl.enter.prevent="submit"
            />
          </UFormField>

          <div class="flex justify-end gap-3 border-t border-default pt-4">
            <UButton type="button" variant="outline" color="neutral" :disabled="saving" @click="() => { open = false }">
              Cancel
            </UButton>
            <UButton type="submit" :disabled="!valid" :loading="saving">
              Save
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
