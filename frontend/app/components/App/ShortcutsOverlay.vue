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
