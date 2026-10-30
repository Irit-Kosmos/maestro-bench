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
import type { Person } from '~/types'

// Someone the app names: their avatar, then their name. `label` says what they did ("Created by"):
// it is read out before the name, and shown on hover when only the avatar is. Nobody is "Former member".
defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  person: Person | null | undefined
  label?: string
  /** The avatar alone, the name in a tooltip: for the rows of a list */
  avatarOnly?: boolean
  size?: '3xs' | '2xs' | 'xs'
}>(), {
  label: undefined,
  avatarOnly: false,
  size: '3xs',
})

const name = computed(() => props.person?.display_name ?? 'Former member')
const tooltip = computed(() => props.label ? `${props.label} ${name.value}` : name.value)
</script>

<template>
  <UTooltip v-if="avatarOnly" :text="tooltip">
    <UAvatar v-bind="$attrs" :src="person?.avatar_url ?? undefined" :alt="name" :size="size" :aria-label="tooltip" role="img" />
  </UTooltip>
  <span v-else v-bind="$attrs" class="inline-flex min-w-0 items-center gap-1.5" :title="label ? tooltip : undefined">
    <UAvatar :src="person?.avatar_url ?? undefined" :alt="name" :size="size" aria-hidden="true" />
    <span v-if="label" class="sr-only">{{ label }} </span>
    <span class="truncate">{{ name }}</span>
  </span>
</template>
