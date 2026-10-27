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
// One line of the analysis settings: what it is on the left, its control on the right
defineProps<{
  label: string
  hint?: string
  required?: boolean
}>()

defineSlots<{ default?: any }>()

const labelId = useId()
</script>

<template>
  <div role="group" :aria-labelledby="labelId" class="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
    <div class="min-w-0">
      <p :id="labelId" class="text-sm text-highlighted">
        {{ label }}<span v-if="required" class="text-error" aria-hidden="true"> *</span>
      </p>
      <p v-if="hint" class="text-xs text-muted text-pretty">
        {{ hint }}
      </p>
    </div>
    <div class="flex min-w-0 flex-wrap gap-1.5 sm:justify-end">
      <slot />
    </div>
  </div>
</template>
