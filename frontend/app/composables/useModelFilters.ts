import type { MaybeRefOrGetter } from 'vue'
import type { Model } from '~/types'
import type { FilterDefinition, FilterState } from '~/utils/filters'
import { countBy, emptyFilterState, hasActiveFilters, matchesFilter } from '~/utils/filters'

export type ModelGroupBy = 'provider' | 'status' | 'none'

export interface ModelGroup {
  key: string
  label: string
  /** Set for provider groups, so the header can draw the logo */
  provider?: string
  models: Model[]
  activeCount: number
}

/**
 * Filtering and grouping of the models list.
 * Providers are compared by their canonical key, so "Together_AI" and "together" are one provider.
 */
export function useModelFilters(source: MaybeRefOrGetter<readonly Model[] | null | undefined>) {
  const search = ref('')
  const modelStatus = (model: Model) => model.is_active ? 'active' : 'inactive'

  // Remembered per browser, like the other list preferences
  const groupBy = useCookie<ModelGroupBy>('models-group-by', { default: () => 'provider' })
  const collapsedKeys = useCookie<string[]>('models-collapsed-groups', { default: () => [] })

  const models = computed(() => toValue(source) ?? [])

  // Offered with the number of models each one has, whatever the other filters say
  const definitions = computed<FilterDefinition[]>(() => {
    const providerCounts = countBy(models.value, model => providerMeta(model.provider).key)
    const statusCounts = countBy(models.value, modelStatus)
    return [
      {
        key: 'provider',
        label: 'Provider',
        icon: 'i-lucide-building-2',
        multiple: true,
        plural: 'providers',
        searchPlaceholder: 'Search a provider…',
        options: [...providerCounts.keys()]
          .map(String)
          .sort(compareProviders)
          .map((key) => {
            const meta = providerMeta(key)
            return {
              value: key,
              label: meta.label,
              icon: meta.icon,
              iconClass: meta.mono ? 'dark:invert' : meta.generic ? 'text-muted' : undefined,
              count: providerCounts.get(key),
            }
          }),
      },
      {
        key: 'status',
        label: 'Status',
        icon: 'i-lucide-circle-dot',
        multiple: false,
        options: [
          { value: 'active', label: 'Active', icon: 'i-lucide-circle-check', count: statusCounts.get('active') ?? 0 },
          { value: 'inactive', label: 'Inactive', icon: 'i-lucide-circle-slash', count: statusCounts.get('inactive') ?? 0 },
        ],
      },
    ]
  })

  const filters = ref<FilterState>(emptyFilterState(definitions.value))

  // Every word must match somewhere: "claude opus" finds "claude-opus-4" and "anthropic haiku" finds Anthropic's Haiku
  const filtered = computed(() => {
    const terms = search.value.toLowerCase().split(/\s+/).filter(Boolean)
    return models.value.filter((model) => {
      if (!matchesFilter(filters.value.provider, providerMeta(model.provider).key) || !matchesFilter(filters.value.status, modelStatus(model)))
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

  const hasFilters = computed(() => !!search.value.trim() || hasActiveFilters(filters.value))

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
    filters.value = emptyFilterState(definitions.value)
  }

  return {
    search,
    filters,
    definitions,
    groupBy,
    filtered,
    groups,
    hasFilters,
    isCollapsed,
    toggleCollapsed,
    clear,
  }
}
