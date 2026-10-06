<script setup lang="ts">
import type { AgentKind } from '~/types'

// What sort of agent this is: one that calls a model, or an aggregator that combines other agents' outputs.
// The two read differently everywhere they are listed, so an aggregator is never taken for a model call.
const props = withDefaults(defineProps<{
  kind?: AgentKind
}>(), {
  kind: 'llm',
})

const aggregator = computed(() => props.kind === 'aggregator')
</script>

<template>
  <UBadge
    :label="aggregator ? 'Aggregator' : 'LLM'"
    :icon="aggregator ? 'i-ph-function-bold' : 'i-ph-ghost-bold'"
    :color="aggregator ? 'info' : 'neutral'"
    variant="subtle"
    size="sm"
  />
</template>
