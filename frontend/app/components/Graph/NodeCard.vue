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
// The card every graph node shares: a small label above, a header, and the node's details in an inset
// panel. Radii are concentric: the panel's is the card's minus the padding between them.
defineProps<{
  /** Small label above the card, e.g. "Step 2" */
  kicker: string
  icon: string
  title: string
  subtitle?: string
  selected?: boolean
  /** The node is switched off: it stays on the graph, but recedes */
  muted?: boolean
  /** Tints the icon: the node is a computation rather than a model call */
  accent?: boolean
}>()

defineSlots<{
  /** Right of the title */
  aside?: () => any
  /** The inset panel */
  default?: () => any
  /** Below the card, outside it */
  footer?: () => any
}>()
</script>

<template>
  <div class="node" :class="{ 'is-selected': selected, 'is-muted': muted }">
    <div class="node-kicker">
      {{ kicker }}
    </div>

    <div class="node-card">
      <header class="node-header">
        <span class="node-tile" :class="{ 'is-accent': accent }">
          <UIcon :name="icon" class="size-4" aria-hidden="true" />
        </span>
        <div class="min-w-0 flex-1">
          <div class="truncate text-sm font-medium text-highlighted" :title="title">
            {{ title }}
          </div>
          <div v-if="subtitle" class="mt-px truncate text-xs text-muted" :title="subtitle">
            {{ subtitle }}
          </div>
        </div>
        <slot name="aside" />
      </header>

      <div v-if="$slots.default" class="node-body">
        <slot />
      </div>
    </div>

    <slot name="footer" />
  </div>
</template>

<style scoped>
.node {
  position: relative;
  transition: opacity 150ms var(--ease-out);
}

.node.is-muted {
  opacity: 0.6;
}

.node-kicker {
  position: absolute;
  bottom: 100%;
  left: 6px;
  margin-bottom: 7px;
  font-size: 10px;
  font-weight: 500;
  line-height: 1;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
  color: var(--ui-text-muted);
  transition: color 150ms var(--ease-out);
}

.node.is-selected .node-kicker {
  color: var(--ui-text-highlighted);
}

.node-card {
  border: 1px solid var(--ui-border);
  border-radius: 14px;
  background: var(--ui-bg);
  padding: 4px;
  box-shadow: 0 1px 2px rgb(0 0 0 / 0.04), 0 6px 14px -8px rgb(0 0 0 / 0.1);
  transition: border-color 150ms var(--ease-out), box-shadow 150ms var(--ease-out);
}

@media (hover: hover) and (pointer: fine) {
  .node:hover .node-card {
    border-color: var(--ui-border-accented);
  }
}

.node.is-selected .node-card {
  border-color: var(--ui-border-inverted);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--ui-text-highlighted) 14%, transparent), 0 6px 14px -8px rgb(0 0 0 / 0.1);
}

.node-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 8px 6px;
}

.node-tile {
  display: grid;
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid var(--ui-border);
  border-radius: 8px;
  background: var(--ui-bg-muted);
  color: var(--ui-text-muted);
}

.node-tile.is-accent {
  border-color: var(--ui-border-accented);
  background: var(--ui-bg-elevated);
  color: var(--ui-text-highlighted);
}

/* 14px card - 4px padding - 1px border: the panel's corners follow the card's */
.node-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border: 1px solid var(--ui-border-muted);
  border-radius: 9px;
  background: var(--ui-bg-muted);
  padding: 8px 10px;
}
</style>
