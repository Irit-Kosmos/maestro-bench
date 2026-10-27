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
import type { FetchErrorKind } from '~/utils/fetchError'

interface Props {
  loading?: boolean
  /** Shown instead of the content (true: the default wording); leave it empty while earlier data is still on screen */
  error?: string | boolean | null
  errorKind?: FetchErrorKind
  /** Where the error state leads back to */
  backTo?: string
  backLabel?: string
  /** Fills the panel instead of growing with its content, so the page itself never scrolls */
  fill?: boolean
}

withDefaults(defineProps<Props>(), {
  loading: false,
  error: null,
  errorKind: 'error',
  backTo: '/',
  backLabel: 'Back to dashboard',
  fill: false,
})

const emit = defineEmits<{
  retry: []
}>()

defineSlots<{
  'default'?: any
  'before-content'?: any
  'after-content'?: any
}>()

// Without a handler the error state reloads the whole app
const onRetry = getCurrentInstance()?.vnode.props?.onRetry ? () => emit('retry') : undefined
</script>

<template>
  <div :class="fill && 'flex flex-col flex-1 min-h-0'">
    <!-- Page actions live in the top bar, next to the breadcrumb, like the rest of the shell -->
    <AppPageActions v-if="$slots['before-content']">
      <slot name="before-content" />
    </AppPageActions>

    <!-- Loading State -->
    <BaseLoadingState v-if="loading" />

    <!-- Error State -->
    <BaseErrorState
      v-else-if="error"
      :kind="errorKind"
      :message="typeof error === 'string' ? error : undefined"
      :action-to="backTo"
      :action-label="backLabel"
      v-bind="onRetry ? { onRetry } : {}"
    />

    <!-- Main Content -->
    <div v-else :class="fill && 'flex flex-col flex-1 min-h-0'">
      <slot />
    </div>

    <!-- After Content Slot -->
    <div v-if="$slots['after-content']">
      <slot name="after-content" />
    </div>
  </div>
</template>
