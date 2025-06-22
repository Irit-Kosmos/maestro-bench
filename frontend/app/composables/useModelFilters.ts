import type { Model } from '~/types'

export function useModelFilters() {
  const selectedProviders = ref<string[]>([])
  const searchQuery = ref<string>('')

  // Filter models based on current filters
  const filterModels = (models: Model[]) => {
    if (!models)
      return []

    return models.filter((model) => {
      // Provider filter (OR condition for multiple providers)
      if (selectedProviders.value.length > 0 && !selectedProviders.value.includes(model.provider)) {
        return false
      }

      // Search filter
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        const matchesName = model.name.toLowerCase().includes(query)
        const matchesProvider = model.provider.toLowerCase().includes(query)
        const matchesDescription = model.description?.toLowerCase().includes(query) || false

        if (!matchesName && !matchesProvider && !matchesDescription) {
          return false
        }
      }

      return true
    })
  }

  // Update filter methods
  const updateProviders = (providers: string[]) => {
    selectedProviders.value = providers
  }

  const toggleProvider = (provider: string) => {
    const index = selectedProviders.value.indexOf(provider)
    if (index > -1) {
      selectedProviders.value.splice(index, 1)
    }
    else {
      selectedProviders.value.push(provider)
    }
  }

  const updateSearch = (query: string) => {
    searchQuery.value = query
  }

  const clearFilters = () => {
    selectedProviders.value = []
    searchQuery.value = ''
  }

  // Computed filter counts
  const getFilterCounts = (models: Model[]) => {
    if (!models)
      return {}

    const counts: Record<string, number> = {}

    // Count by provider
    models.forEach((model) => {
      counts[model.provider] = (counts[model.provider] || 0) + 1
    })

    return counts
  }

  return {
    selectedProviders: readonly(selectedProviders),
    searchQuery: readonly(searchQuery),
    filterModels,
    updateProviders,
    toggleProvider,
    updateSearch,
    clearFilters,
    getFilterCounts,
  }
}
