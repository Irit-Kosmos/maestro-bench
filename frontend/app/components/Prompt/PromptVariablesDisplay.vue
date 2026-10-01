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
  <div>
    <label class="block text-sm font-medium text-default mb-3">
      Variables
    </label>
    <UInputTags
      :model-value="parsedVariables"
      :disabled="!editable"
      class="w-full"
      @update:model-value="updateValue"
    />
  </div>
</template>
