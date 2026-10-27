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
// Rows an execution processed.
// - "warn" (analyses): small samples get a warning badge, icon and tooltip, since their metrics mislead
// - "quiet" (lists): small samples recede, real runs stand out
const props = withDefaults(defineProps<{
  rows?: number | null
  size?: 'xs' | 'sm' | 'md'
  tone?: 'warn' | 'quiet'
}>(), {
  rows: null,
  size: 'sm',
  tone: 'warn',
})

const small = computed(() => isSmallSample(props.rows))
const tooltip = computed(() =>
  props.rows == null ? '' : `Small sample: metrics from ${formatRows(props.rows)} aren’t reliable (under ${SMALL_SAMPLE_ROWS})`,
)
</script>

<template>
  <span v-if="rows === null || rows === undefined" class="text-dimmed">—</span>

  <UTooltip v-else-if="small && tone === 'warn'" :text="tooltip">
    <UBadge
      color="warning"
      variant="soft"
      :size="size"
      icon="i-ph-warning-bold"
      class="tabular-nums"
    >
      {{ formatRows(rows) }}<span class="sr-only">, small sample</span>
    </UBadge>
  </UTooltip>

  <span
    v-else
    class="tabular-nums"
    :class="small ? 'text-muted' : 'font-medium text-highlighted'"
    :title="small ? tooltip : undefined"
  >
    {{ formatRows(rows) }}
  </span>
</template>
