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
// The frame every dashboard block shares: a title, an optional way to see the full list, a body
defineProps<{
  title: string
  /** Where "View all" goes; no link without it */
  to?: string
}>()

defineSlots<{
  /** Small status text, left of the link */
  meta?: any
  default?: any
}>()

const titleId = useId()
</script>

<template>
  <section :aria-labelledby="titleId" class="rounded-lg border border-default overflow-hidden">
    <header class="flex shrink-0 items-center justify-between gap-3 h-11 px-4 border-b border-default">
      <h2 :id="titleId" class="text-sm font-medium text-highlighted">
        {{ title }}
      </h2>
      <div class="flex items-center gap-3">
        <slot name="meta" />
        <UButton
          v-if="to"
          :to="to"
          color="neutral"
          variant="link"
          size="xs"
          trailing-icon="i-ph-arrow-right-bold"
          class="-me-1.5"
          :aria-label="`View all ${title.toLowerCase()}`"
        >
          View all
        </UButton>
      </div>
    </header>
    <slot />
  </section>
</template>
