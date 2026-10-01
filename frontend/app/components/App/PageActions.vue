<script setup lang="ts">
// Renders the page's actions in the top bar, right of the breadcrumb
defineSlots<{ default?: any }>()
</script>

<template>
  <Teleport defer to="#page-actions">
    <slot />
  </Teleport>
</template>
