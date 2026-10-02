<script setup lang="ts">
import type { ModelGroupBy, ModelStatusFilter, ProviderOption } from '~/composables/useModelFilters'

// The toolbar of the models list: search, provider and status filters, and how to group the rows
const props = defineProps<{
  providerOptions: readonly ProviderOption[]
  statusCounts: { all: number, active: number, inactive: number }
  total: number
  shown: number
  hasFilters: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  clear: []
  refresh: []
}>()

const search = defineModel<string>('search', { required: true })
const providers = defineModel<string[]>('providers', { required: true })
const status = defineModel<ModelStatusFilter>('status', { required: true })
const groupBy = defineModel<ModelGroupBy>('groupBy', { required: true })

const searchInput = useTemplateRef<{ inputRef: HTMLInputElement | null }>('searchInput')
defineShortcuts({
  '/': () => searchInput.value?.inputRef?.focus(),
})

const statusItems = computed(() => [
  { label: 'Any status', value: 'all', icon: 'i-lucide-circle-dashed', count: props.statusCounts.all },
  { label: 'Active', value: 'active', icon: 'i-lucide-circle-check', count: props.statusCounts.active },
  { label: 'Inactive', value: 'inactive', icon: 'i-lucide-circle-slash', count: props.statusCounts.inactive },
])

const groupItems = [
  { label: 'Group by provider', value: 'provider', icon: 'i-lucide-layers' },
  { label: 'Group by status', value: 'status', icon: 'i-lucide-list-checks' },
  { label: 'No grouping', value: 'none', icon: 'i-lucide-list' },
]

// The trigger wears the logos of the providers being filtered on
const selectedLogos = computed(() => providers.value.slice(0, 3))

const countLabel = computed(() =>
  props.shown === props.total
    ? `${props.total} ${props.total === 1 ? 'model' : 'models'}`
    : `${props.shown} of ${props.total} models`,
)
</script>

<template>
  <div class="flex min-h-11 flex-wrap items-center gap-x-1 gap-y-1 border-b border-default px-2 py-1">
    <UInput
      ref="searchInput"
      v-model="search"
      placeholder="Filter…"
      icon="i-lucide-search"
      size="sm"
      variant="none"
      aria-label="Filter models"
      class="min-w-32 flex-1 sm:max-w-56"
      @keydown.esc="search = ''"
    >
      <template v-if="!search" #trailing>
        <UKbd value="/" size="sm" />
      </template>
    </UInput>

    <USelectMenu
      v-model="providers"
      multiple
      value-key="value"
      :items="providerOptions as ProviderOption[]"
      :filter-fields="['label', 'value']"
      :search-input="{ placeholder: 'Search providers…' }"
      placeholder="All providers"
      size="xs"
      variant="ghost"
      color="neutral"
      class="w-44"
      :ui="{ content: 'min-w-56' }"
      aria-label="Filter by provider"
    >
      <template #leading>
        <span v-if="selectedLogos.length" class="flex items-center -space-x-1.5">
          <UIProviderIcon v-for="key in selectedLogos" :key="key" :provider="key" />
        </span>
        <UIcon v-else name="i-lucide-building-2" class="size-4 shrink-0 text-dimmed" aria-hidden="true" />
      </template>
      <template #item-leading="{ item }">
        <UIProviderIcon :provider="(item as ProviderOption).value" />
      </template>
      <template #item-trailing="{ item }">
        <span class="text-xs text-dimmed tabular-nums">{{ (item as ProviderOption).count }}</span>
      </template>
    </USelectMenu>

    <USelectMenu
      v-model="status"
      value-key="value"
      :items="statusItems"
      :search-input="false"
      size="xs"
      variant="ghost"
      color="neutral"
      class="w-36"
      aria-label="Filter by status"
    >
      <template #item-trailing="{ item }">
        <span class="text-xs text-dimmed tabular-nums">{{ (item as typeof statusItems[number]).count }}</span>
      </template>
    </USelectMenu>

    <USelectMenu
      v-model="groupBy"
      value-key="value"
      :items="groupItems"
      :search-input="false"
      size="xs"
      variant="ghost"
      color="neutral"
      class="w-40"
      aria-label="Group models"
    />

    <UButton
      v-if="hasFilters"
      color="neutral"
      variant="ghost"
      size="xs"
      icon="i-lucide-x"
      @click="emit('clear')"
    >
      Clear
    </UButton>

    <span class="ms-auto ps-2 text-xs text-muted tabular-nums">{{ countLabel }}</span>
    <UTooltip text="Refresh">
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-lucide-refresh-cw"
        size="sm"
        aria-label="Refresh"
        :loading="loading"
        @click="emit('refresh')"
      />
    </UTooltip>
  </div>
</template>
