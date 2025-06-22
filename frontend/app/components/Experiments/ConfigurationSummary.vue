<script setup lang="ts">
import type { ExperimentExecution } from '~/types'

interface Props {
  latestExecution: ExperimentExecution | null
}

const props = defineProps<Props>()

// Get unique models used in the experiment
const uniqueModels = computed(() => {
  if (!props.latestExecution?.agent_executions)
    return []

  const modelMap = new Map()
  props.latestExecution.agent_executions.forEach((agent) => {
    const key = `${agent.model_provider_snapshot}:${agent.model_name_snapshot}`
    if (!modelMap.has(key)) {
      modelMap.set(key, {
        name: agent.model_name_snapshot,
        provider: agent.model_provider_snapshot,
        count: 0,
      })
    }
    modelMap.get(key).count++
  })

  return Array.from(modelMap.values())
})

// Get unique prompts used in the experiment
const uniquePrompts = computed(() => {
  if (!props.latestExecution?.agent_executions)
    return []

  const promptMap = new Map()
  props.latestExecution.agent_executions.forEach((agent) => {
    const key = `${agent.prompt_name_snapshot}:${agent.prompt_version_snapshot}`
    if (!promptMap.has(key)) {
      promptMap.set(key, {
        name: agent.prompt_name_snapshot,
        version: agent.prompt_version_snapshot,
        count: 0,
      })
    }
    promptMap.get(key).count++
  })

  return Array.from(promptMap.values())
})
</script>

<template>
  <div v-if="latestExecution && latestExecution.agent_executions.length > 0" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <!-- Models Used -->
    <UCard>
      <template #header>
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide-cpu" class="h-6 w-6 text-blue-600" />
          <h2 class="text-xl font-semibold text-neutral-900">
            Models Used
          </h2>
          <UBadge :label="`${uniqueModels.length}`" color="primary" variant="soft" />
        </div>
      </template>

      <div class="space-y-3">
        <div
          v-for="model in uniqueModels"
          :key="`${model.provider}-${model.name}`"
          class="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200"
        >
          <div>
            <div class="font-medium text-blue-900">
              {{ model.name }}
            </div>
            <div class="text-sm text-blue-700">
              {{ model.provider }}
            </div>
          </div>
          <UBadge :label="`${model.count} agent${model.count > 1 ? 's' : ''}`" color="primary" variant="subtle" />
        </div>
      </div>
    </UCard>

    <!-- Prompts Used -->
    <UCard>
      <template #header>
        <div class="flex items-center gap-3">
          <UIcon name="i-lucide-message-square-text" class="h-6 w-6 text-green-600" />
          <h2 class="text-xl font-semibold text-neutral-900">
            Prompts Used
          </h2>
          <UBadge :label="`${uniquePrompts.length}`" color="success" variant="soft" />
        </div>
      </template>

      <div class="space-y-3">
        <div
          v-for="prompt in uniquePrompts"
          :key="`${prompt.name}-${prompt.version}`"
          class="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200"
        >
          <div>
            <div class="font-medium text-green-900">
              {{ prompt.name }}
            </div>
            <div class="text-sm text-green-700">
              Version: {{ prompt.version }}
            </div>
          </div>
          <UBadge :label="`${prompt.count} agent${prompt.count > 1 ? 's' : ''}`" color="success" variant="subtle" />
        </div>
      </div>
    </UCard>
  </div>
</template>
