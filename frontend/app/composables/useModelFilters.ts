import type { MaybeRefOrGetter } from 'vue'
import type { Model } from '~/types'

export type ModelStatusFilter = 'all' | 'active' | 'inactive'
export type ModelGroupBy = 'provider' | 'status' | 'none'

export interface ModelGroup {
  key: string
  label: string
  /** Set for provider groups, so the header can draw the logo */
  provider?: string
  models: Model[]
  activeCount: number
}

export interface ProviderOption {
  /** Canonical provider key */
  value: string
  label: string
  count: number
}

/**
 * Filtering and grouping of the models list.
 * Providers are compared by their canonical key, so "Together_AI" and "together" are one provider.
 */
export function useModelFilters(source: MaybeRefOrGetter<readonly Model[] | null | undefined>) {
  const search = ref('')
  const providers = ref<string[]>([])
  const status = ref<ModelStatusFilter>('all')

  // Remembered per browser, like the other list preferences
  const groupBy = useCookie<ModelGroupBy>('models-group-by', { default: () => 'provider' })
  const collapsedKeys = useCookie<string[]>('models-collapsed-groups', { default: () => [] })

  const models = computed(() => toValue(source) ?? [])

  // Offered with the number of models each one has, whatever the other filters say
  const providerOptions = computed<ProviderOption[]>(() => {
    const counts = new Map<string, number>()
    for (const model of models.value) {
      const key = providerMeta(model.provider).key
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return [...counts.keys()]
      .sort(compareProviders)
      .map(key => ({ value: key, label: providerLabel(key), count: counts.get(key)! }))
  })

  const statusCounts = computed(() => {
    const active = models.value.filter(model => model.is_active).length
    return { all: models.value.length, active, inactive: models.value.length - active }
  })

  // Every word must match somewhere: "claude opus" finds "claude-opus-4" and "anthropic haiku" finds Anthropic's Haiku
  const filtered = computed(() => {
    const terms = search.value.toLowerCase().split(/\s+/).filter(Boolean)
    return models.value.filter((model) => {
      if (providers.value.length && !providers.value.includes(providerMeta(model.provider).key))
        return false
      if (status.value === 'active' && !model.is_active)
        return false
      if (status.value === 'inactive' && model.is_active)
        return false
      if (!terms.length)
        return true
      const haystack = `${model.name} ${providerLabel(model.provider)} ${model.provider} ${model.description ?? ''}`.toLowerCase()
      return terms.every(term => haystack.includes(term))
    })
  })

  const groups = computed<ModelGroup[]>(() => {
    const sorted = filtered.value.toSorted((a, b) => a.name.localeCompare(b.name))
    const make = (key: string, label: string, list: Model[], provider?: string): ModelGroup => ({
      key,
      label,
      provider,
      models: list,
      activeCount: list.filter(model => model.is_active).length,
    })

    if (groupBy.value === 'none')
      return sorted.length ? [make('all', 'All models', sorted)] : []

    if (groupBy.value === 'status') {
      return [
        make('active', 'Active', sorted.filter(model => model.is_active)),
        make('inactive', 'Inactive', sorted.filter(model => !model.is_active)),
      ].filter(group => group.models.length)
    }

    const byProvider = new Map<string, Model[]>()
    for (const model of sorted) {
      const key = providerMeta(model.provider).key
      byProvider.set(key, [...(byProvider.get(key) ?? []), model])
    }
    return [...byProvider.keys()]
      .sort(compareProviders)
      .map(key => make(key, providerLabel(key), byProvider.get(key)!, key))
  })

  const hasFilters = computed(() => !!search.value.trim() || providers.value.length > 0 || status.value !== 'all')

  // A search has to show every match, so it overrides the folded groups
  function isCollapsed(key: string) {
    return !search.value.trim() && collapsedKeys.value.includes(key)
  }

  function toggleCollapsed(key: string) {
    collapsedKeys.value = collapsedKeys.value.includes(key)
      ? collapsedKeys.value.filter(k => k !== key)
      : [...collapsedKeys.value, key]
  }

  function clear() {
    search.value = ''
    providers.value = []
    status.value = 'all'
  }

  return {
    search,
    providers,
    status,
    groupBy,
    providerOptions,
    statusCounts,
    filtered,
    groups,
    hasFilters,
    isCollapsed,
    toggleCollapsed,
    clear,
  }
}
