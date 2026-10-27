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
// Picks the provider of a model, with logos. A provider already stored on the model stays selectable even if it isn't offered.
const model = defineModel<string>({ default: '' })

const items = computed(() => {
  const current = model.value
  const known = PROVIDER_OPTIONS.some(option => option.value === current)
  return current && !known
    ? [...PROVIDER_OPTIONS, { value: current, label: providerLabel(current), icon: providerMeta(current).icon }]
    : PROVIDER_OPTIONS
})
</script>

<template>
  <USelect
    v-model="model"
    :items="items"
    placeholder="Select provider"
  >
    <template #leading="{ modelValue }">
      <UIProviderIcon v-if="modelValue" :provider="modelValue as string" />
      <UIcon v-else name="i-ph-buildings-bold" class="size-4 shrink-0 text-dimmed" aria-hidden="true" />
    </template>
    <template #item-leading="{ item }">
      <UIProviderIcon :provider="(item as { value: string }).value" />
    </template>
  </USelect>
</template>
