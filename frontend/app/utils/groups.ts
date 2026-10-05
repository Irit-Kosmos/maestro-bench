import type { VNodeChild } from 'vue'
import type { FilterOption, FilterValue } from './filters'

type RowKey = string | number

/** A piece of a header's summary, e.g. "2 failed" */
export interface GroupSummaryPart {
  label: string
  /** Classes that tint it, e.g. to flag a problem */
  class?: string
}

/**
 * One way to cut items into sections. An item sits in one section only, so it reads a single value.
 */
export interface GroupLevel<T> {
  /** Names the level on the rows it holds (see `trail`), e.g. "batch" */
  key: string
  value: (item: T) => FilterValue | null | undefined
  /** How a value reads in the section header. Defaults to the value as text. */
  present?: (value: FilterValue) => Pick<FilterOption, 'label' | 'icon' | 'iconClass' | 'dot'>
  /** Muted text after the section name, e.g. what a team is for */
  hint?: (value: FilterValue) => string | null | undefined
  /** Where the section's name leads to, which makes it a reference to that thing */
  link?: (value: FilterValue) => string | null | undefined
  /** What stands out in the section, shown after its count. Nothing to show returns nothing. */
  summary?: (items: readonly T[]) => GroupSummaryPart[]
  /** Fewest items a section needs to get a header; a smaller one dissolves into the level above. Defaults to 1. */
  minSize?: number
  /** Classes that paint the rail running down the rows of the section */
  rail?: string
}

/**
 * A way to cut a list into labelled sections (see the `groups` of BaseDataTable).
 *
 * By default the sections are sorted and the items without a value go to a last section called `emptyLabel`.
 * With `flow`, the list keeps its own order instead: a section sits where its first item was, and the items
 * without a value stay where they are, as plain rows. Only a flowing list can nest a second level with `then`.
 */
export interface GroupSpec<T> extends GroupLevel<T> {
  /** Label and icon of the entry in the group menu */
  label: string
  icon: string
  /** Order of the sections. Defaults to alphabetical by label. */
  compare?: (a: FilterValue, b: FilterValue) => number
  /** Name of the section for the items without a value. Defaults to "None" */
  emptyLabel?: string
  flow?: boolean
  /** A level inside each section; flowing lists only */
  then?: GroupLevel<T>
}

/** What `render` of a table column knows about the row it draws */
export interface RowRenderContext {
  /** Levels of the sections the row sits in, from the outside in (see `GroupLevel.key`); empty when ungrouped */
  trail: string[]
  /**
   * Wraps the part of the content that is the row's own target (its link, or the button that opens it), when
   * that is not all of it: a reference to somewhere else can't sit inside it. Without a call, all of it is the target.
   */
  target: (children: VNodeChild, className?: string) => VNodeChild
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
  to?: string
  summary?: GroupSummaryPart[]
  /** Keys of every row below, collapsed or not: what ticking the header selects */
  keys: RowKey[]
  /** Levels the section sits in, from the outside in; they are what the rail beside the header is drawn from */
  trail: string[]
  /** Level of the section itself */
  level: string
  /** Whether the list flows (see `GroupSpec`), which changes how the header is laid out */
  flow: boolean
}

export interface Section<T> {
  id: string
  value: FilterValue | null
  items: T[]
}

/** The items cut into sections in the order they are shown, the ones without a value last. */
export function groupItems<T>(items: readonly T[], spec: GroupLevel<T> & Pick<GroupSpec<T>, 'compare'>): Section<T>[] {
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

type Entry<T>
  = | { type: 'item', item: T, order: number }
    | { type: 'section', id: string, value: FilterValue, level: GroupLevel<T>, items: T[], children: Entry<T>[], order: number }

/**
 * Cuts the items by the first level, then each section by the next. A flowing list keeps its own order: an entry,
 * item or section, sits where the first item it holds was (`order`).
 */
function sectionize<T>(items: readonly { item: T, index: number }[], levels: readonly GroupLevel<T>[], parentId: string): Entry<T>[] {
  const [level, ...rest] = levels
  if (!level)
    return items.map(({ item, index }) => ({ type: 'item', item, order: index }))

  const buckets = new Map<string, { value: FilterValue | null, items: { item: T, index: number }[] }>()
  for (const entry of items) {
    const value = level.value(entry.item) ?? null
    const id = value === null ? '' : String(value)
    const bucket = buckets.get(id) ?? { value, items: [] }
    bucket.items.push(entry)
    buckets.set(id, bucket)
  }

  const entries: Entry<T>[] = []
  for (const [bucketId, bucket] of buckets) {
    // Without a value, or too few items: no header at this level, the next one cuts what is left
    if (bucket.value === null || bucket.items.length < (level.minSize ?? 1)) {
      entries.push(...sectionize(bucket.items, rest, parentId))
      continue
    }
    const id = `${parentId}${level.key}:${bucketId}/`
    entries.push({
      type: 'section',
      id,
      value: bucket.value,
      level,
      items: bucket.items.map(entry => entry.item),
      children: sectionize(bucket.items, rest, id),
      order: bucket.items[0]!.index,
    })
  }
  return entries.sort((a, b) => a.order - b.order)
}

export interface Arranged<T> {
  /** Items and header stand-ins, in the order they are shown */
  rows: (T | Record<string, unknown>)[]
  /** For each item, the levels it sits in; absent for an item in no section */
  trails: Map<RowKey, string[]>
}

/**
 * The items laid out under their section headers, each header preceded by the stand-in row the table draws it with
 * (see `GROUP_ROW`). A section in `collapsed` shows its header only.
 */
export function arrangeRows<T extends Record<string, any>>(
  items: readonly T[],
  spec: GroupSpec<T>,
  rowKey: string,
  collapsed: ReadonlySet<string>,
): Arranged<T> {
  const trails = new Map<RowKey, string[]>()
  const rows: Arranged<T>['rows'] = []

  const header = (id: string, value: FilterValue | null, level: GroupLevel<T>, sectionItems: readonly T[], trail: string[], flow: boolean) => {
    const present = value === null ? undefined : level.present?.(value)
    const info: GroupRowInfo = {
      id,
      label: value === null ? (spec.emptyLabel ?? 'None') : (present?.label ?? String(value)),
      count: sectionItems.length,
      collapsed: collapsed.has(id),
      icon: present?.icon,
      iconClass: present?.iconClass,
      dot: present?.dot,
      hint: (value === null ? undefined : level.hint?.(value)) ?? undefined,
      to: (value === null ? undefined : level.link?.(value)) ?? undefined,
      summary: level.summary?.(sectionItems).filter(part => part.label),
      keys: sectionItems.map(item => item[rowKey]),
      trail,
      level: level.key,
      flow,
    }
    rows.push({ [rowKey]: `group:${id}`, [GROUP_ROW]: info })
    return info
  }

  if (!spec.flow) {
    for (const section of groupItems(items, spec)) {
      if (!header(section.id, section.value, spec, section.items, [], false).collapsed)
        rows.push(...section.items)
    }
    return { rows, trails }
  }

  const levels = spec.then ? [spec, spec.then] : [spec]
  const emit = (entries: Entry<T>[], trail: string[]) => {
    for (const entry of entries) {
      if (entry.type === 'item') {
        rows.push(entry.item)
        trails.set(entry.item[rowKey], trail)
        continue
      }
      const info = header(entry.id, entry.value, entry.level, entry.items, trail, true)
      if (!info.collapsed)
        emit(entry.children, [...trail, entry.level.key])
    }
  }
  emit(sectionize(items.map((item, index) => ({ item, index })), levels, ''), [])
  return { rows, trails }
}
