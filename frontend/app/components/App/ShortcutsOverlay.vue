<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })

const shortcuts = [
  { section: 'Navigation', items: [
    { keys: ['G', 'H'], label: 'Go to Dashboard' },
    { keys: ['G', 'E'], label: 'Go to Experiments' },
    { keys: ['G', 'D'], label: 'Go to Datasets' },
    { keys: ['G', 'A'], label: 'Go to Agents' },
    { keys: ['G', 'P'], label: 'Go to Prompts' },
    { keys: ['G', 'M'], label: 'Go to Models' },
  ] },
  { section: 'Actions', items: [
    { keys: ['meta', 'K'], label: 'Open command palette' },
    { keys: ['C'], label: 'Create new (context-aware)' },
    { keys: ['?'], label: 'Show keyboard shortcuts' },
  ] },
]
</script>

<template>
  <UModal v-model:open="open" title="Keyboard Shortcuts" :ui="{ content: 'sm:max-w-lg' }">
    <template #body>
      <div class="space-y-6">
        <div v-for="group in shortcuts" :key="group.section">
          <h3 class="text-xs font-medium text-neutral-400 uppercase tracking-wider mb-3">
            {{ group.section }}
          </h3>
          <div class="space-y-2">
            <div
              v-for="shortcut in group.items"
              :key="shortcut.label"
              class="flex items-center justify-between py-1"
            >
              <span class="text-sm text-neutral-700">{{ shortcut.label }}</span>
              <div class="flex items-center gap-1">
                <UKbd v-for="key in shortcut.keys" :key="key" :value="key" size="sm" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </UModal>
</template>
