<script setup lang="ts">
interface Props {
  selectedProviders?: string[]
  searchQuery?: string
  totalCount?: number
  filteredCount?: number
}

interface Emits {
  toggleProvider: [provider: string]
  updateSearch: [query: string]
  clearFilters: []
}

const props = withDefaults(defineProps<Props>(), {
  selectedProviders: () => [],
  searchQuery: '',
  totalCount: 0,
  filteredCount: 0,
})

const emit = defineEmits<Emits>()

// Provider list for quick filters
const providers = ['openai', 'anthropic', 'mistral', 'google', 'meta']

// Local reactive values
const localProviders = ref([...props.selectedProviders])
const localSearch = ref(props.searchQuery || '')

// Watch for prop changes
watch(() => props.selectedProviders, (newVal) => {
  localProviders.value = [...newVal]
})

watch(() => props.searchQuery, (newVal) => {
  localSearch.value = newVal || ''
})

// Methods
function handleProviderToggle(provider: string) {
  const index = localProviders.value.indexOf(provider)
  if (index > -1) {
    localProviders.value.splice(index, 1)
  }
  else {
    localProviders.value.push(provider)
  }
  emit('toggleProvider', provider)
}

function handleSearchChange(value: string) {
  localSearch.value = value
  emit('updateSearch', value)
}

function clearAllFilters() {
  localProviders.value = []
  localSearch.value = ''
  emit('clearFilters')
}

// Computed
const hasActiveFilters = computed(() => {
  return localProviders.value.length > 0 || localSearch.value
})
</script>

<template>
  <div class="space-y-4">
    <!-- Search Bar -->
    <div class="flex gap-4 items-center">
      <div class="flex-1">
        <UInput
          :model-value="localSearch"
          placeholder="Search models..."
          icon="i-heroicons-magnifying-glass"
          class="w-full"
          @update:model-value="handleSearchChange"
        />
      </div>

      <UButton
        v-if="hasActiveFilters"
        variant="outline"
        color="neutral"
        icon="i-heroicons-x-mark"
        @click="clearAllFilters"
      >
        Clear Filters
      </UButton>
    </div>

    <!-- Compact Filters Row -->
    <div class="flex flex-col md:flex-row md:items-center gap-4">
      <!-- Multi-Select Provider Tags -->
      <div class="flex flex-wrap gap-2 md:flex-1">
        <span class="text-sm font-medium text-gray-700 self-center mr-2 whitespace-nowrap">Providers:</span>
        <UButton
          v-for="provider in providers"
          :key="provider"
          :variant="localProviders.includes(provider) ? 'solid' : 'outline'"
          color="neutral"
          size="sm"
          @click="handleProviderToggle(provider)"
        >
          {{ provider.charAt(0).toUpperCase() + provider.slice(1) }}
        </UButton>
      </div>

      <!-- Results Count -->
      <div class="flex gap-4 flex-wrap md:flex-nowrap items-center">
        <div v-if="totalCount > 0" class="text-sm text-gray-600 whitespace-nowrap ml-auto">
          {{ filteredCount }} of {{ totalCount }} models
        </div>
      </div>
    </div>
  </div>
</template>
