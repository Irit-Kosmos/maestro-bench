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
  title: string
  mode: 'create' | 'edit' | 'view'
  loading?: boolean
  /** Holds the submit button back while the form is not valid */
  disabled?: boolean
  size?: 'sm' | 'md' | 'lg' | 'xl'
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  disabled: false,
  size: 'md',
})

const emit = defineEmits<{
  'update:open': [value: boolean]
  'submit': []
  'cancel': []
  'afterLeave': []
}>()

defineSlots<{
  default?: any
  footer?: any
}>()

const isOpen = computed({
  get: () => props.open,
  set: value => emit('update:open', value),
})

const modalTitle = computed(() => {
  const prefix = props.mode === 'create' ? 'Create' : props.mode === 'edit' ? 'Edit' : 'View'
  return `${prefix} ${props.title.toLowerCase()}`
})

const submitLabel = computed(() => {
  return props.mode === 'create' ? 'Create' : props.mode === 'edit' ? 'Save' : 'Close'
})

function handleSubmit() {
  emit('submit')
}

function handleCancel() {
  emit('cancel')
  emit('update:open', false)
}
</script>

<template>
  <UModal v-model:open="isOpen" :title="modalTitle" @after:leave="emit('afterLeave')">
    <template #content>
      <!-- A real form: Enter submits, and the button waits for a valid one -->
      <form @submit.prevent="handleSubmit">
        <UCard class="w-full">
          <template #header>
            <div class="flex items-center justify-between">
              <!-- Not a heading: the modal's own (visually hidden) title already names the dialog -->
              <p class="text-base font-semibold text-highlighted">
                {{ modalTitle }}
              </p>
              <UButton
                type="button"
                variant="ghost"
                color="neutral"
                icon="i-ph-x-bold"
                size="sm"
                aria-label="Close"
                @click="handleCancel"
              />
            </div>
          </template>

          <div class="space-y-4">
            <slot />
          </div>

          <template #footer>
            <slot name="footer">
              <div class="flex justify-end gap-2">
                <UButton
                  v-if="mode !== 'view'"
                  type="button"
                  variant="outline"
                  color="neutral"
                  :disabled="loading"
                  @click="handleCancel"
                >
                  Cancel
                </UButton>
                <UButton
                  type="submit"
                  variant="solid"
                  :color="mode === 'view' ? 'neutral' : 'primary'"
                  :loading="loading"
                  :disabled="disabled"
                >
                  {{ submitLabel }}
                </UButton>
              </div>
            </slot>
          </template>
        </UCard>
      </form>
    </template>
  </UModal>
</template>
