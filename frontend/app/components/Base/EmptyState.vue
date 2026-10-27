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
import type { WorkspaceRole } from '~/types'

interface Props {
  title?: string
  message?: string
  /** Alias of `message` */
  description?: string
  icon?: string
  /** No button unless a label is given */
  actionLabel?: string
  actionIcon?: string
  actionTo?: string
  /** The role the action needs; without it the button is left out, and the text alone says what is missing */
  actionRequires?: WorkspaceRole
}

const props = withDefaults(defineProps<Props>(), {
  title: 'No items found',
  message: undefined,
  description: undefined,
  icon: 'i-ph-folder-open-bold',
  actionLabel: undefined,
  actionIcon: 'i-ph-plus-bold',
  actionTo: undefined,
  actionRequires: undefined,
})

const emit = defineEmits<{
  action: []
}>()

defineSlots<{
  default?: any
}>()

const text = computed(() => props.message ?? props.description)

const { can, workspace } = useCurrentWorkspace()
const allowed = computed(() => !props.actionRequires || can(props.actionRequires))
// What the missing button would have done is not for this person: say who can
const denial = computed(() => props.actionLabel && !allowed.value ? denialReason(workspace.value, props.actionRequires!) : null)

function onAction() {
  if (!props.actionTo)
    emit('action')
}
</script>

<template>
  <div class="flex flex-col items-center text-center py-16 px-4">
    <div class="flex items-center justify-center size-10 rounded-lg bg-elevated ring ring-default mb-4">
      <UIcon :name="icon" class="size-5 text-muted" aria-hidden="true" />
    </div>
    <h3 class="text-sm font-semibold text-highlighted text-balance">
      {{ title }}
    </h3>
    <p v-if="text" class="mt-1 max-w-sm text-sm text-muted text-pretty">
      {{ text }}
    </p>
    <p v-if="denial" class="mt-2 max-w-sm text-xs text-muted text-pretty">
      {{ denial }}.
    </p>
    <div v-if="$slots.default || (actionLabel && allowed)" class="mt-5 flex items-center gap-2">
      <slot>
        <UButton
          :to="actionTo"
          color="neutral"
          variant="soft"
          :icon="actionIcon"
          size="sm"
          @click="onAction"
        >
          {{ actionLabel }}
        </UButton>
      </slot>
    </div>
  </div>
</template>
