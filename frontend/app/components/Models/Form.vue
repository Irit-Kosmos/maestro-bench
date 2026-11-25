<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
export interface ModelFormValues {
  name: string
  provider: string
  description: string
  max_tokens: number | null
  supports_temperature: boolean
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

// A model that takes no temperature keeps no default one
watch(() => form.value.supports_temperature, (supported) => {
  if (!supported)
    form.value.default_temperature = null
})

// Open from the start when the model already sets some of the advanced fields
// (the modal mounts the form each time it opens, with the values in place)
const advancedOpen = ref(
  form.value.max_tokens != null
  || form.value.default_max_tokens != null
  || form.value.default_temperature != null
  || !form.value.supports_temperature,
)

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

    <div class="flex items-center justify-between gap-3 rounded-md border border-default px-3 h-8 sm:col-span-2">
      <label class="text-sm text-default" for="model-active">Active</label>
      <USwitch id="model-active" v-model="form.is_active" size="sm" />
    </div>

    <!-- The tuning most models do without: folded away unless the model sets some of it -->
    <UCollapsible v-model:open="advancedOpen" class="group/advanced sm:col-span-2">
      <button
        type="button"
        class="flex w-full cursor-pointer items-center gap-2 rounded-md py-1 text-start text-sm font-medium text-highlighted outline-none focus-visible:outline-2 focus-visible:outline-inverted"
      >
        <UIcon name="i-ph-caret-right-bold" class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) group-data-[state=open]/advanced:rotate-90 motion-reduce:transition-none" aria-hidden="true" />
        Advanced settings
        <span class="truncate text-xs font-normal text-muted">Context window, max tokens, temperature</span>
      </button>
      <template #content>
        <div class="grid grid-cols-1 gap-4 pt-3 sm:grid-cols-2">
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

          <div class="flex items-center justify-between gap-3 self-end rounded-md border border-default px-3 h-8">
            <label class="text-sm text-default" for="model-supports-temperature">Supports temperature</label>
            <USwitch id="model-supports-temperature" v-model="form.supports_temperature" size="sm" />
          </div>

          <UFormField v-if="form.supports_temperature" label="Default temperature">
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
        </div>
      </template>
    </UCollapsible>
  </div>
</template>
