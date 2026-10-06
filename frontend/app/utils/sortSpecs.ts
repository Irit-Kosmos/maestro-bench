import type { SortSpec } from './sorts'
import { STATUS_ORDER } from './filterSpecs'
import { parseApiDate } from './utils'

// Sorts that several lists share. Icon names stay literal strings so Nuxt Icon can find and serve them.

/** Items by their name, A to Z. */
export function nameSort<T>(name: (item: T) => string | null | undefined, label = 'Name'): SortSpec<T> {
  return { key: 'name', label, icon: 'i-ph-text-aa-bold', value: item => name(item)?.trim() || null }
}

/** Items by a date, the latest first. An unreadable date goes last. */
export function dateSort<T>(date: (item: T) => string | null | undefined, label = 'Created'): SortSpec<T> {
  return {
    key: `date-${label.toLowerCase()}`,
    label,
    icon: 'i-ph-calendar-blank-bold',
    defaultDirection: 'desc',
    value: (item) => {
      const value = date(item)
      return value ? parseApiDate(value).getTime() : null
    },
  }
}

/** Items by where their run stands, in the order a run goes through the statuses. */
export function statusSort<T>(status: (item: T) => string | null | undefined): SortSpec<T> {
  return {
    key: 'status',
    label: 'Status',
    icon: 'i-ph-radio-button-bold',
    value: (item) => {
      const rank = STATUS_ORDER.indexOf(status(item) ?? '')
      return rank < 0 ? null : rank
    },
  }
}

/** Items by a figure, the biggest first. A figure that is not known yet goes last. */
export function figureSort<T>(key: string, label: string, icon: string, value: (item: T) => number | null | undefined): SortSpec<T> {
  return { key, label, icon, defaultDirection: 'desc', value }
}

/** Items by a piece of text, A to Z. An item without one goes last. */
export function textSort<T>(key: string, label: string, icon: string, value: (item: T) => string | null | undefined): SortSpec<T> {
  return { key, label, icon, value: item => value(item)?.trim() || null }
}
