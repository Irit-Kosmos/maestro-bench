<script setup lang="ts">
// The variables a prompt declares, written the way the prompt marks them in its text: monospace on a light tint.
// Pointing at one (or focusing it) sets `active`, so the text can pick it out.
const props = defineProps<{
  variables: string | null
}>()

const active = defineModel<string | null>('active', { default: null })

const parsedVariables = computed(() => parseVariables(props.variables || ''))
</script>

<template>
  <section>
    <h3 class="mb-1.5 flex h-6 items-center text-xs font-medium text-muted">
      Variables
    </h3>

    <ul v-if="parsedVariables.length" class="flex flex-wrap gap-1">
      <li v-for="name in parsedVariables" :key="name">
        <code
          tabindex="0"
          class="block rounded-sm px-1.5 py-0.5 font-mono text-xs text-primary outline-none transition-colors duration-100 focus-visible:ring-2 focus-visible:ring-inverted"
          :class="name === active ? 'bg-primary/25' : 'bg-primary/10'"
          @pointerenter="active = name"
          @pointerleave="active = null"
          @focus="active = name"
          @blur="active = null"
        >{{ name }}</code>
      </li>
    </ul>
    <p v-else class="text-sm text-dimmed">
      None
    </p>
  </section>
</template>
