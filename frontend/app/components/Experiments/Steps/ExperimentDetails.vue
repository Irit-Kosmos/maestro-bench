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
  <div class="mt-6 max-w-xl flex flex-col gap-4">
    <UFormField label="Name" required>
      <UInput
        v-model="name"
        placeholder="e.g. Corrector agent test v2.1"
        class="w-full"
        autofocus
      />
    </UFormField>

    <UFormField label="Description" hint="Optional">
      <UTextarea
        v-model="description"
        placeholder="What are you testing?"
        :rows="2"
        autoresize
        class="w-full"
      />
    </UFormField>
  </div>
</template>
