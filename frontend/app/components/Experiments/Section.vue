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
// A titled block of an experiment page (the form, the results). Sections stack, separated by a rule.
defineProps<{
  id: string
  title: string
  description?: string
  /** Tighter rhythm, for sections in a side column */
  compact?: boolean
  /** Names what the section is about, before its title */
  icon?: string
  /** How many things it holds, after its title */
  count?: number
}>()

defineSlots<{
  default?: any
  actions?: any
}>()
</script>

<template>
  <section
    :id="id"
    :aria-labelledby="`${id}-title`"
    class="scroll-mt-6 border-t border-default first:border-t-0 first:pt-0"
    :class="compact ? 'pt-5' : 'pt-8'"
  >
    <div class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 sm:flex-nowrap">
      <div class="min-w-0">
        <h2 :id="`${id}-title`" class="flex items-center gap-2 text-base font-semibold text-highlighted">
          <UIcon v-if="icon" :name="icon" class="size-4 shrink-0 text-muted" aria-hidden="true" />
          {{ title }}
          <span v-if="count !== undefined" class="text-sm font-normal text-muted tabular-nums">{{ count }}</span>
        </h2>
        <p v-if="description" class="mt-0.5 max-w-prose text-sm text-muted text-pretty">
          {{ description }}
        </p>
      </div>
      <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2">
        <slot name="actions" />
      </div>
    </div>
    <div :class="compact ? 'mt-3' : 'mt-4'">
      <slot />
    </div>
  </section>
</template>
