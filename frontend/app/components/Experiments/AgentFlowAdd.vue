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
  if (armConnect && (e.target as Element).closest('[data-add-button]'))
    armConnect(e, props.nodeId)
}

const items = computed(() => agentMenuItems(available.value, agent => addAfter(props.nodeId, agent)))
</script>

<template>
  <div v-if="items.length > 0" class="absolute top-full left-1/2 flex -translate-x-1/2 flex-col items-center" @pointerdown="onPress">
    <span class="h-4 w-[1.5px] bg-(--graph-edge)" aria-hidden="true" />
    <UDropdownMenu :items="items" :content="{ side: 'bottom', align: 'center', sideOffset: 6 }" :ui="{ content: 'min-w-48 max-h-72' }">
      <!-- The hit area (::after) is the whole 36px around the dot, not just the dot. Hovering the node it hangs from
           already lights it up -->
      <button
        type="button"
        class="relative grid size-6 place-items-center rounded-full border border-dashed border-accented bg-default text-muted transition-[border-color,color,background-color,scale] duration-150 ease-out after:absolute after:-inset-1.5 group-hover/graph-node:border-(--ui-text-muted) group-hover/graph-node:text-highlighted hover:border-solid hover:border-(--ui-text-muted) hover:bg-elevated hover:text-highlighted active:scale-[0.92] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-inverted data-[state=open]:border-solid data-[state=open]:border-inverted data-[state=open]:text-highlighted"
        aria-label="Add the next agent, or drag to connect an agent"
        data-add-button
        data-graph-ui
      >
        <UIcon name="i-ph-plus-bold" class="size-3" aria-hidden="true" />
      </button>
    </UDropdownMenu>
  </div>
</template>
