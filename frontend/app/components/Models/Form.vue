<script setup lang="ts">
export interface ModelFormValues {
  name: string
  provider: string
  description: string
  max_tokens: number | null
  default_temperature: number | null
  default_max_tokens: number | null
  is_active: boolean
}

// The fields of a model, shared by "Add model" and "Edit model"
defineProps<{
  /** Example name shown in the empty field */
  namePlaceholder?: string
}>()

const form = defineModel<ModelFormValues>({ required: true })
</script>

<template>
  <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
    <UFormField label="Name" required class="sm:col-span-2">
      <UInput
        v-model="form.name"
        :placeholder="namePlaceholder"
        required
        autocomplete="off"
        class="w-full"
      />
    </UFormField>

    <UFormField label="Provider" required class="sm:col-span-2">
      <ModelsProviderSelect v-model="form.provider" class="w-full" />
    </UFormField>

    <UFormField label="Description" class="sm:col-span-2">
      <UTextarea
        v-model="form.description"
        placeholder="Brief description of the model"
        :rows="2"
        class="w-full"
      />
    </UFormField>

    <UFormField label="Context window" hint="Tokens">
      <UInput
        v-model="form.max_tokens"
        type="number"
        min="1"
        placeholder="e.g. 128000"
        class="w-full"
      />
    </UFormField>

    <UFormField label="Default max tokens" hint="Tokens">
      <UInput
        v-model="form.default_max_tokens"
        type="number"
        min="1"
        placeholder="e.g. 2048"
        class="w-full"
      />
    </UFormField>

    <UFormField label="Default temperature">
      <UInput
        v-model="form.default_temperature"
        type="number"
        step="0.1"
        min="0"
        max="2"
        placeholder="e.g. 0.7"
        class="w-full"
      />
    </UFormField>

    <div class="flex items-center justify-between gap-3 self-end rounded-md border border-default px-3 h-8">
      <label class="text-sm text-default" for="model-active">Active</label>
      <USwitch id="model-active" v-model="form.is_active" size="sm" />
    </div>
  </div>
</template>
