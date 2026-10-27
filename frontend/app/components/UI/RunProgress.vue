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
import type { RunState } from '~/types'

// The class of the caller (margins, alignment) belongs to the collapsing wrapper
defineOptions({ inheritAttrs: false })

// Rows a running execution has processed: a bar and the count, with the failed ones named.
// Nothing once the run is over, where the figures live with the run itself
defineProps<{
  run?: RunState | null
}>()
</script>

<template>
  <!-- Collapses when the run ends, so the row it sits in doesn't lose its height in one jump -->
  <Transition name="reveal">
    <div v-if="run?.status === 'running'" v-bind="$attrs" class="reveal">
      <div class="flex items-center gap-2 text-xs text-muted tabular-nums">
        <UProgress
          :model-value="run.rows_total ? run.rows_done : null"
          :max="run.rows_total || 1"
          size="xs"
          class="w-20"
          aria-label="Rows processed"
        />
        <span>{{ run.rows_done }}<template v-if="run.rows_total"> / {{ run.rows_total }}</template></span>
        <span v-if="run.rows_failed" class="text-error">{{ run.rows_failed }} failed</span>
      </div>
    </div>
  </Transition>
</template>
