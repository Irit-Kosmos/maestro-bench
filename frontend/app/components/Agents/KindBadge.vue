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
import type { AgentKind } from '~/types'

// What sort of agent this is: one that calls a model, or an aggregator that combines other agents' outputs.
// The two read differently everywhere they are listed, so an aggregator is never taken for a model call.
const props = withDefaults(defineProps<{
  kind?: AgentKind
}>(), {
  kind: 'llm',
})

const aggregator = computed(() => props.kind === 'aggregator')
</script>

<template>
  <UBadge
    :label="aggregator ? 'Aggregator' : 'LLM'"
    :icon="aggregator ? 'i-ph-function-bold' : 'i-ph-ghost-bold'"
    :color="aggregator ? 'info' : 'neutral'"
    variant="subtle"
    size="sm"
  />
</template>
