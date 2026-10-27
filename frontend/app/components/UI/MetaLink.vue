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
// A link inside a meta line: an arrow that is always there (it is what says "this is a link"), and nudges on hover/focus
// Behind a public link a link only works for what the link reaches: the pages that know theirs say so
// with `in-share`, the others read as text
defineProps<{
  to: string
  inShare?: boolean
}>()

const { isShared } = useShare()
</script>

<template>
  <span v-if="isShared && !inShare" class="min-w-0 truncate text-toned"><slot /></span>
  <NuxtLink
    v-else
    :to="to"
    class="group/link inline-flex min-w-0 items-center gap-1 rounded text-toned outline-none transition-colors hover:text-highlighted focus-visible:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
  >
    <span class="truncate underline-offset-2 group-hover/link:underline"><slot /></span>
    <UIcon
      name="i-ph-arrow-right-bold"
      class="size-3.5 shrink-0 text-muted transition duration-200 ease-out group-hover/link:translate-x-0.5 group-hover/link:text-highlighted group-focus-visible/link:translate-x-0.5 group-focus-visible/link:text-highlighted motion-reduce:transition-none"
      aria-hidden="true"
    />
  </NuxtLink>
</template>
