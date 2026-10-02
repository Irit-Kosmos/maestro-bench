<script setup lang="ts">
interface Props {
  variables: string | null
  editable?: boolean
  modelValue?: string[]
}

interface Emits {
  'update:modelValue': [value: string[]]
}

const props = withDefaults(defineProps<Props>(), {
  editable: false,
})

const emit = defineEmits<Emits>()

const parsedVariables = computed(() => {
  if (props.editable && props.modelValue) {
    return props.modelValue
  }
  return parseVariables(props.variables || '')
})

function updateValue(value: string[]) {
  if (props.editable) {
    emit('update:modelValue', value)
  }
}
</script>

<template>
  <section>
    <h3 class="mb-1.5 flex h-6 items-center text-xs font-medium text-muted">
      Variables
    </h3>

    <UInputTags
      v-if="editable"
      :model-value="parsedVariables"
      placeholder="Type a name, press Enter"
      class="w-full"
      @update:model-value="updateValue"
    />

    <ul v-else-if="parsedVariables.length" class="flex flex-wrap gap-1.5">
      <li v-for="name in parsedVariables" :key="name">
        <UBadge :label="name" color="neutral" variant="subtle" size="md" class="font-mono" />
      </li>
    </ul>
    <p v-else class="text-sm text-dimmed">
      None
    </p>
  </section>
</template>
