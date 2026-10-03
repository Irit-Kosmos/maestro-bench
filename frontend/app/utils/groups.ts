import type { FilterOption, FilterValue } from './filters'

/**
 * A way to cut a list into labelled sections (see the `groups` of BaseDataTable). An item sits in one section only,
 * so it reads a single value; the items with none go to a last section called `emptyLabel`.
 */
export interface GroupSpec<T> {
  key: string
  label: string
  icon: string
  value: (item: T) => FilterValue | null | undefined
  /** How a value reads in the section header. Defaults to the value as text. */
  present?: (value: FilterValue) => Pick<FilterOption, 'label' | 'icon' | 'iconClass' | 'dot'>
  /** Muted text after the section name, e.g. what a team is for */
  hint?: (value: FilterValue) => string | null | undefined
  /** Order of the sections. Defaults to alphabetical by label. */
  compare?: (a: FilterValue, b: FilterValue) => number
  /** Name of the section for the items without a value. Defaults to "None" */
  emptyLabel?: string
}

/** Property that marks the stand-in rows a grouped table puts before each section */
export const GROUP_ROW = '__group'

export interface GroupRowInfo {
  /** Stable id of the section, for collapsing it */
  id: string
  label: string
  count: number
  collapsed: boolean
  icon?: string
  iconClass?: string
  dot?: string
  hint?: string
}

export interface Section<T> {
  id: string
  value: FilterValue | null
  items: T[]
}

/** The items cut into sections in the order they are shown, the ones without a value last. */
export function groupItems<T>(items: readonly T[], spec: GroupSpec<T>): Section<T>[] {
  const found = new Map<string, Section<T>>()
  for (const item of items) {
    const value = spec.value(item) ?? null
    const id = value === null ? '' : String(value)
    const section = found.get(id) ?? { id, value, items: [] }
    section.items.push(item)
    found.set(id, section)
  }
  const label = (value: FilterValue) => spec.present?.(value).label ?? String(value)
  return [...found.values()].sort((a, b) => {
    if (a.value === null || b.value === null)
      return Number(a.value === null) - Number(b.value === null)
    return spec.compare ? spec.compare(a.value, b.value) : label(a.value).localeCompare(label(b.value), undefined, { numeric: true })
  })
}
