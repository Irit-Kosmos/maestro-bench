<script setup lang="ts">
// A button of the canvas's floating toolbar. Tooltips come from the toolbar's UITooltipGroup (data-tooltip)
defineProps<{
  label: string
  icon?: string
  kbd?: string
  disabled?: boolean
  pressed?: boolean
}>()
</script>

<template>
  <button
    type="button"
    class="graph-control"
    :aria-label="label"
    :aria-pressed="pressed"
    :data-tooltip="label"
    :data-tooltip-kbds="kbd"
    :disabled="disabled"
  >
    <slot>
      <UIcon v-if="icon" :name="icon" class="size-3.5" aria-hidden="true" />
    </slot>
  </button>
</template>

<style>
.graph-control {
  display: inline-flex;
  height: 1.75rem;
  min-width: 1.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--ui-text-muted);
  transition: background-color 120ms var(--ease-out), color 120ms var(--ease-out), scale 120ms var(--ease-out);
}

@media (hover: hover) and (pointer: fine) {
  .graph-control:not(:disabled):hover {
    background: var(--ui-bg-elevated);
    color: var(--ui-text-highlighted);
  }
}

.graph-control:not(:disabled):active {
  scale: 0.95;
}

.graph-control[aria-pressed='true'] {
  color: var(--ui-text-highlighted);
}

.graph-control:disabled {
  opacity: 0.4;
  cursor: default;
}

.graph-control:focus-visible {
  outline: 2px solid var(--ui-border-inverted);
  outline-offset: -1px;
}
</style>
