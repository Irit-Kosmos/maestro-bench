import type { FilterSpec } from './filters'
import type { Tag } from '~/types'
import { byOrder } from './filters'
import { tagDot } from './tags'
import { parseApiDate } from './utils'

// Filters that several lists share. Icon names stay literal strings so Nuxt Icon can find and serve them.

// Same colours as the status icon of the tables
const STATUSES = {
  pending: { label: 'Pending', icon: 'i-lucide-circle-dashed', iconClass: 'text-muted' },
  running: { label: 'Running', icon: 'i-lucide-loader-circle', iconClass: 'text-warning' },
  completed: { label: 'Completed', icon: 'i-lucide-circle-check', iconClass: 'text-success' },
  partial: { label: 'Partial', icon: 'i-lucide-circle-alert', iconClass: 'text-warning' },
  failed: { label: 'Failed', icon: 'i-lucide-circle-x', iconClass: 'text-error' },
  cancelled: { label: 'Cancelled', icon: 'i-lucide-circle-slash', iconClass: 'text-muted' },
} as const

type KnownStatus = keyof typeof STATUSES

const isKnownStatus = (value: unknown): value is KnownStatus => typeof value === 'string' && value in STATUSES

const presentStatus = (value: unknown) => isKnownStatus(value) ? STATUSES[value] : { label: String(value) }

/** Where a run stands, in the order a run goes through them. */
export function statusFilter<T>(status: (item: T) => string | null | undefined): FilterSpec<T> {
  return {
    key: 'status',
    label: 'Status',
    icon: 'i-lucide-circle-dot',
    plural: 'statuses',
    value: status,
    present: presentStatus,
    compare: byOrder(Object.keys(STATUSES)),
  }
}

/** The statuses the executions before the latest one ended with, which the status filter reads. */
export function earlierRunsFilter<T>(statuses: (item: T) => readonly string[] | null | undefined): FilterSpec<T> {
  return {
    key: 'earlier_runs',
    label: 'Earlier runs',
    icon: 'i-lucide-history',
    plural: 'statuses',
    value: item => [...new Set(statuses(item))],
    present: presentStatus,
    compare: byOrder(Object.keys(STATUSES)),
  }
}

/** The dataset an item was run on, by name. */
export function datasetFilter<T>(name: (item: T) => string | null | undefined): FilterSpec<T> {
  return {
    key: 'dataset',
    label: 'Dataset',
    icon: 'i-lucide-database',
    plural: 'datasets',
    searchPlaceholder: 'Search a dataset…',
    value: name,
  }
}

const DAY_MS = 24 * 60 * 60 * 1000

// A date belongs to every window it falls in, so "Last 7 days" also holds what happened today
const DATE_RANGES = [
  { value: 'day', label: 'Last 24 hours', days: 1 },
  { value: 'week', label: 'Last 7 days', days: 7 },
  { value: 'month', label: 'Last 30 days', days: 30 },
] as const

const OLDER = { value: 'older', label: 'Older than 30 days' } as const

/** The ranges a date falls in, from the narrowest to the widest; "older" when it is in none. Nothing for an unreadable date. */
export function dateRanges(date: string, now = Date.now()): string[] {
  const age = now - parseApiDate(date).getTime()
  if (Number.isNaN(age))
    return []
  const ranges: string[] = DATE_RANGES.filter(range => age <= range.days * DAY_MS).map(range => range.value)
  return ranges.length ? ranges : [OLDER.value]
}

/** How long ago something happened, as one of a few windows. */
export function dateFilter<T>(date: (item: T) => string | null | undefined, label = 'Created'): FilterSpec<T> {
  const options = [...DATE_RANGES, OLDER]
  const labels = new Map<string, string>(options.map(option => [option.value, option.label]))
  return {
    key: `date-${label.toLowerCase()}`,
    label,
    icon: 'i-lucide-calendar',
    multiple: false,
    value: (item) => {
      const value = date(item)
      return value ? dateRanges(value) : undefined
    },
    present: value => ({ label: labels.get(String(value)) ?? String(value) }),
    compare: byOrder(options.map(option => option.value)),
  }
}

const RUNS = {
  none: { label: 'Never run' },
  once: { label: 'Run once' },
  several: { label: 'Run several times' },
} as const

/**
 * Whether the experiments were run again. `executions` counts the executions of the item and
 * `experiments` the experiments they are spread over (a batch holds several, an experiment is one).
 * Nothing for an item whose count is unknown.
 */
export function runsFilter<T>(executions: (item: T) => number | null | undefined, experiments: (item: T) => number = () => 1): FilterSpec<T> {
  return {
    key: 'runs',
    label: 'Runs',
    icon: 'i-lucide-repeat',
    value: (item) => {
      const count = executions(item)
      if (count == null)
        return undefined
      return count === 0 ? 'none' : count > experiments(item) ? 'several' : 'once'
    },
    present: value => RUNS[value as keyof typeof RUNS] ?? { label: String(value) },
    compare: byOrder(Object.keys(RUNS)),
  }
}

const FAILURES = {
  failed: { label: 'With failed rows', icon: 'i-lucide-triangle-alert', iconClass: 'text-error' },
  clean: { label: 'No failed rows' },
} as const

/** Whether the latest execution had rows that failed. Nothing while there is no execution to tell. */
export function failuresFilter<T>(rowsFailed: (item: T) => number | null | undefined): FilterSpec<T> {
  return {
    key: 'failures',
    label: 'Failures',
    icon: 'i-lucide-triangle-alert',
    multiple: false,
    value: (item) => {
      const count = rowsFailed(item)
      return count == null ? undefined : count > 0 ? 'failed' : 'clean'
    },
    present: value => FAILURES[value as keyof typeof FAILURES] ?? { label: String(value) },
    compare: byOrder(Object.keys(FAILURES)),
  }
}

/** The tags an item carries, picked by name. An item can carry several, so "is all of" is offered. */
export function tagsFilter<T>(tags: (item: T) => readonly Tag[] | null | undefined): FilterSpec<T> {
  // The colour of each tag, learnt from the items as the filter reads them
  const colors = new Map<string, string>()
  return {
    key: 'tags',
    label: 'Tags',
    icon: 'i-lucide-tag',
    plural: 'tags',
    multiValued: true,
    searchPlaceholder: 'Search a tag…',
    value: (item) => {
      const found = tags(item) ?? []
      for (const tag of found)
        colors.set(tag.name, tag.color)
      return found.map(tag => tag.name)
    },
    present: value => ({ label: String(value), dot: tagDot(colors.get(String(value)) ?? 'gray') }),
  }
}
