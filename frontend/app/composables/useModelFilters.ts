import type { MaybeRefOrGetter } from 'vue'
import type { Model } from '~/types'
import type { FilterSpec } from '~/utils/filters'
import type { GroupSpec } from '~/utils/groups'
import type { SortSpec } from '~/utils/sorts'
import { useLocalStorage } from '@vueuse/core'
import { byOrder } from '~/utils/filters'
import { activeSortSpec, sortItems } from '~/utils/sorts'
import { figureSort, nameSort, textSort } from '~/utils/sortSpecs'

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
    icon: 'i-ph-buildings-bold',
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
    icon: 'i-ph-radio-button-bold',
    multiple: false,
    value: model => model.is_active ? 'active' : 'inactive',
    present: value => value === 'active'
      ? { label: 'Active', icon: 'i-ph-check-circle-bold', iconClass: 'text-success' }
      : { label: 'Inactive', icon: 'i-ph-prohibit-bold', iconClass: 'text-muted' },
    compare: byOrder(['active', 'inactive']),
  },
]

// The entries of the group menu, the same one the tables have
export const modelGroups: Pick<GroupSpec<Model>, 'key' | 'label' | 'icon'>[] = [
  { key: 'provider', label: 'Provider', icon: 'i-ph-buildings-bold' },
  { key: 'status', label: 'Status', icon: 'i-ph-radio-button-bold' },
]

// In the order of the columns. Without one the models are by name; inside a group they are sorted among themselves
export const modelSorts: SortSpec<Model>[] = [
  nameSort(model => model.name, 'Model'),
  textSort('provider', 'Provider', 'i-ph-buildings-bold', model => providerLabel(model.provider)),
  figureSort('context', 'Context', 'i-ph-ruler-bold', model => model.max_tokens),
  figureSort('temperature', 'Temperature', 'i-ph-thermometer-bold', model => model.default_temperature),
  // Active first when ascending
  { key: 'status', label: 'Status', icon: 'i-ph-radio-button-bold', value: model => model.is_active ? 0 : 1 },
]

function modelSearchText(model: Model) {
  return `${model.name} ${providerLabel(model.provider)} ${model.provider} ${model.description ?? ''}`
}

/** Filtering, grouping and sorting of the models list. */
export function useModelFilters(source: MaybeRefOrGetter<readonly Model[] | null | undefined>) {
  const { search, filters, definitions, filtered, hasFilters, clear } = useListFilters(source, modelFilterSpecs, modelSearchText)

  // Remembered per browser, like the other list preferences
  const groupBy = useGroupBy('maestro:models-group-by', 'provider')
  const sortBy = useSortBy('maestro:models-sort-by')
  const collapsedKeys = useLocalStorage<string[]>(workspaceStorageKey('maestro:models-collapsed-groups'), [])

  const groups = computed<ModelGroup[]>(() => {
    const sort = activeSortSpec(modelSorts, sortBy.value)
    const sorted = sort
      ? sortItems(filtered.value, sort, sortBy.value!.direction)
      : filtered.value.toSorted((a, b) => a.name.localeCompare(b.name))
    const make = (key: string, label: string, list: Model[], provider?: string): ModelGroup => ({
      key,
      label,
      provider,
      models: list,
      activeCount: list.filter(model => model.is_active).length,
    })

    if (!groupBy.value)
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
    sortBy,
    filtered,
    groups,
    hasFilters,
    isCollapsed,
    toggleCollapsed,
    clear,
  }
}
