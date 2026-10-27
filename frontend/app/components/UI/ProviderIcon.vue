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
// A provider's logo. Black logos flip to white on dark surfaces; providers without a logo get a muted stand-in.
const props = defineProps<{
  provider: string | null | undefined
  // Sits on an always-light surface, so black logos stay black in dark mode
  onLight?: boolean
}>()

const meta = computed(() => providerMeta(props.provider))
</script>

<template>
  <UIcon
    :name="meta.icon"
    class="size-4 shrink-0"
    :class="[meta.mono && !onLight && 'dark:invert', meta.generic && !onLight && 'text-muted']"
    aria-hidden="true"
  />
</template>
