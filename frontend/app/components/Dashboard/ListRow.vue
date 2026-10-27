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
// A row that opens something: one link across the whole row, so the hit area is the row
defineProps<{ to: string }>()
</script>

<template>
  <!-- Hover is instant on purpose: rows are scanned and hovered constantly -->
  <NuxtLink
    :to="to"
    class="flex flex-wrap items-center gap-x-3 gap-y-1 min-h-11 px-4 py-1.5 outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
  >
    <slot />
  </NuxtLink>
</template>
