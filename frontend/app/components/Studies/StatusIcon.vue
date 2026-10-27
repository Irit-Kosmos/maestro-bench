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
// A study's status as an icon: each has its own shape, so it still reads without colour
const props = withDefaults(defineProps<{
  status: string
  /** Tailwind size class of the icon */
  size?: string
  /** Rich tooltip with the status in words, instead of the native title */
  tooltip?: boolean
}>(), {
  size: 'size-3.5',
  tooltip: false,
})

const meta = computed(() => studyStatusMeta(props.status))
</script>

<template>
  <UTooltip :text="`${meta.label}: ${meta.description}`" :disabled="!tooltip">
    <span class="inline-flex shrink-0 items-center align-middle" :title="tooltip ? undefined : meta.label">
      <UIcon :name="meta.icon" :class="[size, meta.tone]" aria-hidden="true" />
      <span class="sr-only">{{ meta.label }}</span>
    </span>
  </UTooltip>
</template>
