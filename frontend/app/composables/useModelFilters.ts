import type { MaybeRefOrGetter } from 'vue'
import type { Model } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import { byOrder } from '~/utils/filters'

export type ModelGroupBy = 'provider' | 'status' | 'none'

export interface ModelGroup {
  key: string
  label: string
  /** Set for provider groups, so the header can draw the logo */
  provider?: string
  models: Model[]
  activeCount: number
}

// Providers are compared by their canonical key, so "Together_AI" and "together" are one provider
const modelProvider = (model: Model) => providerMeta(model.provider).key

const modelFilterSpecs: FilterSpec<Model>[] = [
  {
    key: 'provider',
    label: 'Provider',
    icon: 'i-lucide-building-2',
    plural: 'providers',
    searchPlaceholder: 'Search a provider…',
    value: modelProvider,
    present: (key) => {
      const meta = providerMeta(String(key))
      return {
        label: meta.label,
        icon: meta.icon,
        iconClass: meta.mono ? 'dark:invert' : meta.generic ? 'text-muted' : undefined,
      }
    },
    compare: (a, b) => compareProviders(String(a), String(b)),
  },
  {
    key: 'status',
    label: 'Status',
    icon: 'i-lucide-circle-dot',
    multiple: false,
    value: model => model.is_active ? 'active' : 'inactive',
    present: value => value === 'active'
      ? { label: 'Active', icon: 'i-lucide-circle-check', iconClass: 'text-success' }
      : { label: 'Inactive', icon: 'i-lucide-circle-slash', iconClass: 'text-muted' },
    compare: byOrder(['active', 'inactive']),
  },
]

function modelSearchText(model: Model) {
  return `${model.name} ${providerLabel(model.provider)} ${model.provider} ${model.description ?? ''}`
}

/** Filtering and grouping of the models list. */
export function useModelFilters(source: MaybeRefOrGetter<readonly Model[] | null | undefined>) {
  const { search, filters, definitions, filtered, hasFilters, clear } = useListFilters(source, modelFilterSpecs, modelSearchText)

  // Remembered per browser, like the other list preferences
  const groupBy = useCookie<ModelGroupBy>('models-group-by', { default: () => 'provider' })
  const collapsedKeys = useCookie<string[]>('models-collapsed-groups', { default: () => [] })

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
      const key = modelProvider(model)
      byProvider.set(key, [...(byProvider.get(key) ?? []), model])
    }
    return [...byProvider.keys()]
      .sort(compareProviders)
      .map(key => make(key, providerLabel(key), byProvider.get(key)!, key))
  })

  // A search has to show every match, so it overrides the folded groups
  function isCollapsed(key: string) {
    return !search.value.trim() && collapsedKeys.value.includes(key)
  }

  function toggleCollapsed(key: string) {
    collapsedKeys.value = collapsedKeys.value.includes(key)
      ? collapsedKeys.value.filter(k => k !== key)
      : [...collapsedKeys.value, key]
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
