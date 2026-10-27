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
// UKbd renders arrows as text glyphs, which fall back to another font and sit off-center in the key
const props = defineProps<{ value: string }>()

const ICONS: Record<string, string> = {
  'enter': 'i-ph-arrow-elbow-down-left-bold',
  '↑': 'i-ph-arrow-up-bold',
  '↓': 'i-ph-arrow-down-bold',
  '←': 'i-ph-arrow-left-bold',
  '→': 'i-ph-arrow-right-bold',
}

// The key's name, for screen readers: the icon says nothing to them
const NAMES: Record<string, string> = {
  'enter': 'Enter',
  '↑': 'Up arrow',
  '↓': 'Down arrow',
  '←': 'Left arrow',
  '→': 'Right arrow',
}

const icon = computed(() => ICONS[props.value])
</script>

<template>
  <UKbd v-if="icon" size="sm" class="align-middle">
    <UIcon :name="icon" class="size-2.5" aria-hidden="true" />
    <span class="sr-only">{{ NAMES[value] }}</span>
  </UKbd>
  <UKbd v-else :value="value" size="sm" class="align-middle" />
</template>
