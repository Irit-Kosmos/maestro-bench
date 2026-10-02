export type FilterValue = string | number | boolean

export interface FilterOption {
  value: FilterValue
  label: string
  icon?: string
  /** Extra classes for the icon in the option list, e.g. to flip a black logo on dark surfaces. */
  iconClass?: string
  /** How many items carry this value, shown next to the option. */
  count?: number
}

export interface FilterDefinition {
  key: string
  label: string
  icon: string
  /** Checkboxes when true, a single choice (radio) otherwise. */
  multiple: boolean
  options: FilterOption[]
  /**
   * Items can carry several values at once (the techs of a project), which makes
   * "is all of" meaningful. Leave it off when each item has a single value, like a year.
   */
  multiValued?: boolean
  /** Used in the chip once several values are picked, e.g. "3 techs". */
  plural?: string
  searchPlaceholder?: string
}

/**
 * How the selected values combine: `include` keeps items carrying any of them, `all` items
 * carrying every one of them, `exclude` items carrying none of them.
 */
export type FilterMode = 'include' | 'all' | 'exclude'

export interface FilterEntry {
  mode: FilterMode
  /** Single-choice filters hold zero or one value, so every filter reads the same way: empty means inactive. */
  values: FilterValue[]
}

/** Filter entry per filter key. */
export type FilterState = Record<string, FilterEntry>

export function emptyFilterEntry(): FilterEntry {
  return { mode: 'include', values: [] }
}

export function emptyFilterState(definitions: FilterDefinition[]): FilterState {
  return Object.fromEntries(definitions.map(definition => [definition.key, emptyFilterEntry()]))
}

export function hasActiveFilters(state: FilterState) {
  return Object.values(state).some(entry => entry.values.length)
}

/** Modes a filter offers: single-choice filters only ever read "is". */
export function filterModes(definition: FilterDefinition): FilterMode[] {
  if (!definition.multiple)
    return ['include']
  return definition.multiValued ? ['include', 'all', 'exclude'] : ['include', 'exclude']
}

/**
 * With a single value, "all of" and "any of" select the same items, so both read "is".
 * Callers compare against this rather than the stored mode to know what the chip says.
 */
export function effectiveMode(entry: FilterEntry): FilterMode {
  return entry.mode === 'all' && entry.values.length < 2 ? 'include' : entry.mode
}

const MODE_LABELS: Record<FilterMode, [single: string, several: string]> = {
  include: ['is', 'is any of'],
  all: ['is', 'is all of'],
  exclude: ['is not', 'is none of'],
}

export function modeLabel(mode: FilterMode, count: number) {
  return MODE_LABELS[mode][count > 1 ? 1 : 0]
}

/** An empty filter lets everything through; otherwise the item's values are checked against the mode. */
export function matchesFilter(entry: FilterEntry | undefined, values: FilterValue | FilterValue[] | undefined) {
  if (!entry?.values.length)
    return true
  const list = Array.isArray(values) ? values : [values]
  switch (entry.mode) {
    case 'all':
      return entry.values.every(value => list.includes(value))
    case 'exclude':
      return !entry.values.some(value => list.includes(value))
    default:
      return entry.values.some(value => list.includes(value))
  }
}

/** How many items carry each value, for the counts shown next to the options. */
export function countBy<T>(items: readonly T[], getValues: (item: T) => FilterValue | FilterValue[] | undefined) {
  const counts = new Map<FilterValue, number>()
  for (const item of items) {
    const values = getValues(item)
    for (const value of Array.isArray(values) ? values : [values]) {
      if (value !== undefined)
        counts.set(value, (counts.get(value) ?? 0) + 1)
    }
  }
  return counts
}

/**
 * A filter declared against the items of a list: how to read the value(s) an item carries, and how to present them.
 * The options are found in the items, so only values that exist are offered (see `buildFilterDefinitions`).
 */
export interface FilterSpec<T> {
  key: string
  label: string
  icon: string
  /** Value(s) an item carries; none when null or undefined. */
  value: (item: T) => FilterValue | FilterValue[] | null | undefined
  /** Several values can be picked. Defaults to true; false for a single choice. */
  multiple?: boolean
  multiValued?: boolean
  plural?: string
  searchPlaceholder?: string
  /** How a value reads in the option list and the chip. Defaults to the value as text. */
  present?: (value: FilterValue) => Pick<FilterOption, 'label' | 'icon' | 'iconClass'>
  /** Order of the options. Defaults to alphabetical by label. */
  compare?: (a: FilterValue, b: FilterValue) => number
}

/** Orders values as listed, for a fixed vocabulary such as statuses. Unlisted values come last. */
export function byOrder(order: readonly FilterValue[]) {
  const rank = (value: FilterValue) => {
    const index = order.indexOf(value)
    return index === -1 ? order.length : index
  }
  return (a: FilterValue, b: FilterValue) => rank(a) - rank(b)
}

// A missing value is undefined everywhere downstream, whether the item said null or nothing
const valueOf = <T>(spec: FilterSpec<T>, item: T) => spec.value(item) ?? undefined

/**
 * The definitions the filter bar needs, with the number of items each option has.
 * A filter whose items carry no value at all is left out, since there is nothing to pick.
 */
export function buildFilterDefinitions<T>(items: readonly T[], specs: readonly FilterSpec<T>[]): FilterDefinition[] {
  return specs
    .map((spec) => {
      const counts = countBy(items, item => valueOf(spec, item))
      const present = spec.present ?? ((value: FilterValue) => ({ label: String(value) }))
      const compare = spec.compare ?? ((a: FilterValue, b: FilterValue) => present(a).label.localeCompare(present(b).label))
      return {
        key: spec.key,
        label: spec.label,
        icon: spec.icon,
        multiple: spec.multiple ?? true,
        multiValued: spec.multiValued,
        plural: spec.plural,
        searchPlaceholder: spec.searchPlaceholder,
        options: [...counts.keys()].sort(compare).map(value => ({ value, ...present(value), count: counts.get(value) })),
      }
    })
    .filter(definition => definition.options.length)
}

/** Whether an item passes every filter. */
export function matchesSpecs<T>(item: T, specs: readonly FilterSpec<T>[], state: FilterState) {
  return specs.every(spec => matchesFilter(state[spec.key], valueOf(spec, item)))
}

/** The words of a search box. */
export function searchTerms(search: string) {
  return search.toLowerCase().split(/\s+/).filter(Boolean)
}

/** Every word must match somewhere: "claude opus" finds "claude-opus-4", whatever the order of the words. */
export function matchesTerms(text: string, terms: readonly string[]) {
  if (!terms.length)
    return true
  const haystack = text.toLowerCase()
  return terms.every(term => haystack.includes(term))
}
