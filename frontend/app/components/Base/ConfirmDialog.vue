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
interface Props {
  open: boolean
  title?: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  variant?: 'error' | 'warning' | 'info'
  loading?: boolean
  /** Why the action failed; shown in the dialog, which stays open so the person can try again */
  error?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  title: 'Confirm',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  variant: 'warning',
  loading: false,
  error: null,
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'confirm': []
  'cancel': []
  'afterLeave': []
}>()

const isOpen = computed({
  get: () => props.open,
  set: value => emit('update:open', value),
})

const confirmColor = computed(() => ({ error: 'error', warning: 'warning', info: 'primary' } as const)[props.variant])

function handleConfirm() {
  emit('confirm')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <UModal
    v-model:open="isOpen"
    :title="title"
    :description="message"
    :dismissible="!loading"
    @after:leave="emit('afterLeave')"
  >
    <template v-if="error" #body>
      <UAlert color="error" variant="subtle" icon="i-ph-warning-circle-bold" :description="error" />
    </template>

    <template #footer>
      <div class="flex w-full justify-end gap-2">
        <UButton variant="outline" color="neutral" :disabled="loading" @click="handleCancel">
          {{ cancelLabel }}
        </UButton>
        <UButton variant="solid" :color="confirmColor" :loading="loading" @click="handleConfirm">
          {{ confirmLabel }}
        </UButton>
      </div>
    </template>
  </UModal>
</template>
