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

// A date cell of a list, led by who made the item: their avatar, then how long ago. The avatar keeps its
// place when nobody is known, so the dates of a column stay aligned.
const props = withDefaults(defineProps<{
  date: string
  person?: Person | null
  /** What the person did, for the tooltip of the avatar */
  label?: string
}>(), {
  person: null,
  label: 'Created by',
})

const { formatDate, formatRelativeDate } = useUIHelpers()
</script>

<template>
  <span class="flex items-center gap-2">
    <span class="flex size-4 shrink-0">
      <!-- Above the row's link, so that its tooltip opens -->
      <UIPerson v-if="props.person" :person="props.person" :label="label" avatar-only class="relative z-1" />
    </span>
    <span class="text-sm text-muted" :title="formatDate(date)">{{ formatRelativeDate(date) }}</span>
  </span>
</template>
