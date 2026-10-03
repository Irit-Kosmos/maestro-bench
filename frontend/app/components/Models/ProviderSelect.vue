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
