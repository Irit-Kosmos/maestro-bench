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

// The fields of a model, shared by "New model" and "Edit model"
defineProps<{
  /** Example name shown in the empty field */
  namePlaceholder?: string
}>()

const form = defineModel<ModelFormValues>({ required: true })

const { lacksCredentials, missingKeyAdvice } = useProviderStatus()
const { isOwner } = useCurrentWorkspace()
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
      <p v-if="lacksCredentials(form.provider)" class="mt-1.5 flex items-start gap-1.5 text-xs text-warning">
        <UIcon name="i-ph-warning-bold" class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        <span>
          No API key for {{ providerMeta(form.provider).label }}: runs with this model will fail.
          <NuxtLink v-if="isOwner" to="/settings" class="underline underline-offset-2">Add one in Settings.</NuxtLink>
          <template v-else>{{ missingKeyAdvice }}</template>
        </span>
      </p>
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
