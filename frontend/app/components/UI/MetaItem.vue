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
// One fact in a page's meta line: a quiet icon, then the value
defineProps<{
  icon: string
  /** Names the fact for assistive tech and on hover, since the icon alone doesn't */
  label: string
}>()
</script>

<template>
  <span class="inline-flex min-w-0 items-center gap-1.5" :title="label">
    <UIcon :name="icon" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
    <span class="sr-only">{{ label }}: </span>
    <slot />
  </span>
</template>
