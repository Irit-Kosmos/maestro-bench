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
import type { Agent } from '~/types'

// The "+" under a node nothing reads from yet: pick an agent and it is added right after, already connected
const props = defineProps<{ nodeId: string }>()

const available = inject<Ref<Agent[]>>('agentFlowAvailable', ref([]))
const addAfter = inject<(nodeId: string, agent: Agent) => void>('agentFlowAddAfter', () => {})

const armConnect = inject<((e: PointerEvent, nodeId: string) => void) | undefined>('graphArmConnect', undefined)

// A press on the button may be the start of a drag to another agent: the canvas watches it, and takes over once it
// travels. The menu opens on click, which a drag never produces
function onPress(e: PointerEvent) {
  if (armConnect && (e.target as Element).closest('.add-button'))
    armConnect(e, props.nodeId)
}

const items = computed(() => agentMenuItems(available.value, agent => addAfter(props.nodeId, agent)))
</script>

<template>
  <div v-if="items.length > 0" class="add" @pointerdown="onPress">
    <span class="add-stem" aria-hidden="true" />
    <UDropdownMenu :items="items" :content="{ side: 'bottom', align: 'center', sideOffset: 6 }" :ui="{ content: 'min-w-48 max-h-72' }">
      <button type="button" class="add-button" aria-label="Add the next agent, or drag to connect an agent" data-graph-ui>
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
      </button>
    </UDropdownMenu>
  </div>
</template>

<style scoped>
.add {
  position: absolute;
  top: 100%;
  left: 50%;
  display: flex;
  translate: -50% 0;
  flex-direction: column;
  align-items: center;
}

.add-stem {
  width: 1.5px;
  height: 16px;
  background: var(--graph-edge);
}

.add-button {
  position: relative;
  display: grid;
  width: 24px;
  height: 24px;
  place-items: center;
  border: 1px dashed var(--ui-border-accented);
  border-radius: 999px;
  background: var(--ui-bg);
  color: var(--ui-text-muted);
  transition: border-color 150ms var(--ease-out), color 150ms var(--ease-out), background-color 150ms var(--ease-out), scale 120ms var(--ease-out);
}

/* The hit area is the whole 36px around the dot, not just the dot */
.add-button::after {
  position: absolute;
  inset: -6px;
  content: '';
}

@media (hover: hover) and (pointer: fine) {
  .add-button:hover,
  :global(.graph-node:hover) .add-button {
    border-color: var(--ui-text-muted);
    color: var(--ui-text-highlighted);
  }

  .add-button:hover {
    border-style: solid;
    background: var(--ui-bg-elevated);
  }
}

.add-button:active {
  scale: 0.92;
}

.add-button[data-state='open'] {
  border-style: solid;
  border-color: var(--ui-border-inverted);
  color: var(--ui-text-highlighted);
}

.add-button:focus-visible {
  outline: 2px solid var(--ui-border-inverted);
  outline-offset: 2px;
}
</style>
