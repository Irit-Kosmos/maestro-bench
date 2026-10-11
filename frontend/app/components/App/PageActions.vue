<script setup lang="ts">
// Renders the page's actions in the top bar, right of the breadcrumb. They share one tooltip that slides from
// button to button: describe a button with data-tooltip rather than wrapping it in a UTooltip.
defineSlots<{ default?: any }>()
</script>

<template>
  <Teleport defer to="#page-actions">
    <UITooltipGroup>
      <slot />
    </UITooltipGroup>
  </Teleport>
</template>
