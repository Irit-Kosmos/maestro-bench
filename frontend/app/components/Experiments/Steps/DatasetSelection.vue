<script setup lang="ts">
interface Props {
  selectedDataset?: number
}

interface Emits {
  'update:selectedDataset': [value: number | undefined]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const { datasets } = useDatasets()

// Two-way binding computed property
const selectedDataset = computed({
  get: () => props.selectedDataset,
  set: (value: number | undefined) => emit('update:selectedDataset', value),
})
</script>

<template>
  <div class="space-y-2 flex flex-col gap-2 mt-4">
    <div class="max-w-md mx-auto w-full">
      <UFormField label="Available Datasets" required>
        <USelect
          v-model="selectedDataset"
          :items="datasets?.map(d => ({ label: `${d.name} - ${d.description}`, value: d.id })) || []"
          placeholder="Select a dataset..."
          size="lg"
          class="w-full"
        />
      </UFormField>
      <p class="text-xs text-neutral-500 mt-2">
        The dataset contains the questions/tasks for your experiment
      </p>
    </div>

    <!-- Dataset Preview - Collapsible -->
    <div v-if="selectedDataset">
      <UCollapsible :default-open="false" class="mx-auto w-full mt-4">
        <UButton
          label="Dataset Preview"
          color="neutral"
          variant="subtle"
          leading-icon="i-lucide-eye"
          trailing-icon="i-lucide-chevron-down"
          class="group"
          :ui="{
            trailingIcon: 'group-data-[state=open]:rotate-180 transition-transform duration-200',
          }"
        />

        <template #content>
          <div class="p-1 mt-2">
            <DatasetsPreview :dataset-id="selectedDataset" />
          </div>
        </template>
      </UCollapsible>
    </div>
  </div>
</template>
