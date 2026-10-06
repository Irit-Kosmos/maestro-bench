<script setup lang="ts">
const props = defineProps<{
  variables: string | null
}>()

const parsedVariables = computed(() => parseVariables(props.variables || ''))
</script>

<template>
  <section>
    <h3 class="mb-1.5 flex h-6 items-center text-xs font-medium text-muted">
      Variables
    </h3>

    <ul v-if="parsedVariables.length" class="flex flex-wrap gap-1.5">
      <li v-for="name in parsedVariables" :key="name">
        <UBadge :label="name" color="neutral" variant="subtle" size="md" class="font-mono" />
      </li>
    </ul>
    <p v-else class="text-sm text-dimmed">
      None
    </p>
  </section>
</template>
