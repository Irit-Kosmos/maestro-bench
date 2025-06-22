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
  <div class="flex flex-col justify-center">
    <div class="max-w-md mx-auto w-full mt-4">
      <div class="space-y-4">
        <UFormField label="Experiment Name" required>
          <UInput
            v-model="name"
            size="lg"
            placeholder="e.g., 'Corrector Agent Test v2.1'"
            class="w-full"
          />
        </UFormField>

        <UFormField label="Description">
          <UTextarea
            v-model="description"
            placeholder="Optional description of this experiment"
            :rows="3"
            class="w-full"
          />
        </UFormField>
      </div>
      <p class="text-xs text-neutral-500 mt-4">
        Use a clear, descriptive name for easy identification
      </p>
    </div>
  </div>
</template>
