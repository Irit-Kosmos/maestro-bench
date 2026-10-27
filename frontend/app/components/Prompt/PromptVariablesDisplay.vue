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
// The variables a prompt declares, written the way the prompt marks them in its text: monospace on a light tint.
// Pointing at one (or focusing it) sets `active`, so the text can pick it out.
const props = defineProps<{
  variables: string | null
}>()

const active = defineModel<string | null>('active', { default: null })

const parsedVariables = computed(() => parseVariables(props.variables || ''))
</script>

<template>
  <section>
    <h3 class="mb-1.5 flex h-6 items-center text-xs font-medium text-muted">
      Variables
    </h3>

    <ul v-if="parsedVariables.length" class="flex flex-wrap gap-1">
      <li v-for="name in parsedVariables" :key="name">
        <code
          tabindex="0"
          class="block rounded-sm px-1.5 py-0.5 font-mono text-xs text-primary-700 outline-none dark:text-primary transition-colors duration-100 focus-visible:ring-2 focus-visible:ring-inverted"
          :class="name === active ? 'bg-primary/25' : 'bg-primary/10'"
          @pointerenter="active = name"
          @pointerleave="active = null"
          @focus="active = name"
          @blur="active = null"
        >{{ name }}</code>
      </li>
    </ul>
    <p v-else class="text-sm text-muted">
      None
    </p>
  </section>
</template>
