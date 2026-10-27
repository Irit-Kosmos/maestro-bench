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
const open = defineModel<boolean>('open', { default: false })

const shortcuts = [
  { section: 'Navigation', items: [
    { keys: ['G', 'H'], label: 'Go to Dashboard' },
    { keys: ['G', 'E'], label: 'Go to Experiments' },
    { keys: ['G', 'B'], label: 'Go to Batches' },
    { keys: ['G', 'N'], label: 'Go to Analyses' },
    { keys: ['G', 'D'], label: 'Go to Datasets' },
    { keys: ['G', 'P'], label: 'Go to Prompts' },
    { keys: ['G', 'M'], label: 'Go to Models' },
    { keys: ['G', 'A'], label: 'Go to Agents' },
    { keys: ['G', 'Y'], label: 'Go to Studies' },
    { keys: ['G', 'S'], label: 'Go to Settings' },
    { keys: ['O', 'W'], label: 'Switch workspace' },
  ] },
  { section: 'Actions', items: [
    { keys: ['meta', 'K'], label: 'Open command palette' },
    { keys: ['C'], label: 'New item on this page (an experiment elsewhere)' },
    { keys: ['meta', 'B'], label: 'Collapse or expand the sidebar' },
    { keys: ['T'], label: 'Switch between light and dark' },
    { keys: ['meta', 'I'], label: 'Show or hide the properties of a study' },
    { keys: ['?'], label: 'Show keyboard shortcuts' },
  ] },
  { section: 'Dataset rows', items: [
    { keys: ['/'], label: 'Search rows' },
    { keys: ['↑', '↓', '←', '→'], label: 'Move between cells' },
    { keys: ['enter'], label: 'Edit the selected cell (enter saves it, esc cancels)' },
    { keys: ['space'], label: 'Open the row in full' },
    { keys: ['X'], label: 'Select the row' },
    { keys: ['delete'], label: 'Delete the selected rows' },
    { keys: ['meta', 'S'], label: 'Save the dataset' },
  ] },
]
</script>

<template>
  <UModal v-model:open="open" title="Keyboard shortcuts" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div class="space-y-6">
        <div v-for="group in shortcuts" :key="group.section">
          <h3 class="text-xs font-medium text-muted mb-2">
            {{ group.section }}
          </h3>
          <div>
            <div
              v-for="shortcut in group.items"
              :key="shortcut.label"
              class="flex items-center justify-between py-1.5"
            >
              <span class="text-sm text-default">{{ shortcut.label }}</span>
              <div class="flex items-center gap-1">
                <BaseKbd v-for="key in shortcut.keys" :key="key" :value="key" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </UModal>
</template>
