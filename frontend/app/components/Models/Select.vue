<script setup lang="ts">
import type { Model } from '~/types'

// Picks one model (or several) from the catalogue: grouped by provider, searchable by model or provider name.
// Inactive models are hidden, except the ones already chosen so an existing setup never breaks.
const props = withDefaults(defineProps<{
  models: readonly Model[]
  placeholder?: string
  multiple?: boolean
  /** Lets the choice be cleared (the value becomes null) */
  clearable?: boolean
  /** Shown ticked and fixed, labelled "Current setup": the value the others are compared to */
  lockedId?: number | null
  searchPlaceholder?: string
}>(), {
  placeholder: 'Choose a model',
  lockedId: null,
  searchPlaceholder: 'Search models or providers…',
})

const model = defineModel<number | number[] | null | undefined>({ default: undefined })

const selectedIds = computed(() => new Set(
  (Array.isArray(model.value) ? model.value : [model.value]).filter((id): id is number => typeof id === 'number'),
))

// Typed loosely: label rows and model rows share one list, which the menu's own typing can't express
const items = computed<any[][]>(() => {
  const byProvider = new Map<string, Model[]>()
  for (const m of props.models) {
    if (!m.is_active && !selectedIds.value.has(m.id) && m.id !== props.lockedId)
      continue
    const key = providerMeta(m.provider).key
    byProvider.set(key, [...(byProvider.get(key) ?? []), m])
  }

  return [...byProvider.keys()].sort(compareProviders).map(key => [
    { type: 'label' as const, label: providerLabel(key) },
    ...byProvider.get(key)!
      .toSorted((a, b) => a.name.localeCompare(b.name))
      .map(m => ({
        label: m.name,
        value: m.id,
        providerKey: key,
        providerLabel: providerLabel(key),
        context: m.max_tokens ? formatTokens(m.max_tokens) : null,
        inactive: !m.is_active,
        description: m.id === props.lockedId ? 'Current setup' : undefined,
        disabled: m.id === props.lockedId,
      })),
  ])
})

const modelsById = computed(() => new Map(props.models.map(m => [m.id, m])))

// The trigger wears the logo of the chosen model, or the logos of the chosen providers when there are several
const leadingProviders = computed(() => {
  const keys = [...selectedIds.value].map(id => modelsById.value.get(id)?.provider).filter(Boolean) as string[]
  return [...new Set(keys.map(p => providerMeta(p).key))].slice(0, 3)
})

function onUpdate(value: unknown) {
  // Clearing a single select reports undefined; the callers' forms use null for "none"
  model.value = (props.clearable && (value === undefined || value === null) && !props.multiple ? null : value) as typeof model.value
}
</script>

<template>
  <USelectMenu
    :model-value="(model ?? undefined) as any"
    :multiple="multiple"
    :clear="clearable && !multiple"
    value-key="value"
    :items="items"
    :filter-fields="['label', 'providerLabel', 'providerKey']"
    :placeholder="placeholder"
    :search-input="{ placeholder: searchPlaceholder }"
    :ui="{ content: 'min-w-64' }"
    @update:model-value="onUpdate"
  >
    <template #leading>
      <span v-if="leadingProviders.length" class="flex items-center -space-x-1.5">
        <UIProviderIcon v-for="key in leadingProviders" :key="key" :provider="key" />
      </span>
      <UIcon v-else name="i-lucide-cpu" class="size-4 shrink-0 text-dimmed" aria-hidden="true" />
    </template>

    <template #item-leading="{ item }">
      <UIProviderIcon :provider="(item as any).providerKey" />
    </template>

    <template #item-trailing="{ item }">
      <span v-if="(item as any).inactive" class="text-xs text-warning">Inactive</span>
      <span v-else-if="(item as any).context" class="text-xs text-dimmed tabular-nums" title="Context window">{{ (item as any).context }}</span>
    </template>
  </USelectMenu>
</template>
