<script setup lang="ts">
interface Props {
  experimentDetails: {
    name: string
    description: string
  }
}

interface Emits {
  'update:name': [value: string]
  'update:description': [value: string]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Two-way binding computed properties
const name = computed({
  get: () => props.experimentDetails.name,
  set: (value: string) => emit('update:name', value),
})

const description = computed({
  get: () => props.experimentDetails.description,
  set: (value: string) => emit('update:description', value),
})
</script>

<template>
  <div class="mt-4">
    <div class="max-w-4xl mx-auto w-full">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <UFormField label="Experiment Name" required>
          <UInput
            v-model="name"
            placeholder="e.g., 'Corrector Agent Test v2.1'"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Description">
          <UInput
            v-model="description"
            placeholder="Optional description"
            class="w-full"
          />
        </UFormField>
      </div>
    </div>
  </div>
</template>
