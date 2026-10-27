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

// A button for an action that needs a role. Out of reach, it stays visible but disabled, and a tooltip says
// why, so nobody wonders where the function went. Everything else goes to the underlying UButton.
defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  requires?: WorkspaceRole
  /** The action is still allowed in an archived workspace (stopping something, say) */
  archivedOk?: boolean
}>(), {
  requires: 'editor',
  archivedOk: false,
})

const { denial, workspace } = useCurrentWorkspace()
// Behind a public link there is nothing to do but read: the action is not there, instead of there and refused
const { isShared } = useShare()
const reason = computed(() => props.archivedOk
  ? denialReason(workspace.value && { ...workspace.value, archived: false }, props.requires)
  : denial(props.requires))
// In a tooltip group (the top bar), the group's shared tooltip says why
const inGroup = inject(tooltipGroupKey, false)
</script>

<template>
  <template v-if="isShared" />
  <UTooltip v-else-if="reason" :text="reason" :disabled="inGroup">
    <!-- A disabled button swallows hover: the wrapper is what the tooltip listens to -->
    <span class="inline-flex" tabindex="0" :data-tooltip="inGroup ? reason : undefined">
      <UButton v-bind="{ ...$attrs, onClick: undefined, to: undefined }" disabled>
        <slot />
      </UButton>
    </span>
  </UTooltip>
  <UButton v-else v-bind="$attrs">
    <slot />
  </UButton>
</template>
