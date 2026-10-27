// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

export type SortDirection = 'asc' | 'desc'

/** How a list is sorted: by which entry of the sort menu, and which way. */
export interface SortState {
  key: string
  direction: SortDirection
}

/** What a sort reads on an item. An item without a value (null, undefined, NaN) goes last, whichever way the list is sorted. */
export type SortValue = string | number | null | undefined

/**
 * One thing a list can be sorted on, an entry of the sort menu.
 */
export interface SortSpec<T> {
  key: string
  /** Label and icon of the entry in the sort menu */
  label: string
  icon: string
  value: (item: T) => SortValue
  /** Way the list goes when the entry is picked. Defaults to ascending; dates and figures are read biggest first. */
  defaultDirection?: SortDirection
}

const isMissing = (value: SortValue): value is null | undefined => value == null || (typeof value === 'number' && Number.isNaN(value))

function compareValues(a: string | number, b: string | number) {
  if (typeof a === 'number' && typeof b === 'number')
    return a - b
  // "Run 2" comes before "Run 10"
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' })
}

/** The items in the order the spec reads them. Items that read equal keep their place, and the ones without a value stay last. */
export function sortItems<T>(items: readonly T[], spec: SortSpec<T>, direction: SortDirection): T[] {
  const sign = direction === 'asc' ? 1 : -1
  // Read once per item, not once per comparison
  const keyed = items.map(item => ({ item, value: spec.value(item) }))
  return keyed.toSorted((a, b) => {
    const missingA = isMissing(a.value)
    const missingB = isMissing(b.value)
    if (missingA || missingB)
      return Number(missingA) - Number(missingB)
    return sign * compareValues(a.value as string | number, b.value as string | number)
  }).map(entry => entry.item)
}

/** The sort the state stands for, or nothing when it names an entry the list does not offer (a stale choice). */
export function activeSortSpec<T>(specs: readonly SortSpec<T>[], state: SortState | null | undefined): SortSpec<T> | null {
  return specs.find(spec => spec.key === state?.key) ?? null
}

/** The state that picking an entry gives. Picking the one in use again keeps its direction. */
export function pickSort<T>(spec: SortSpec<T>, current: SortState | null | undefined): SortState {
  return { key: spec.key, direction: current?.key === spec.key ? current.direction : spec.defaultDirection ?? 'asc' }
}

const SEPARATOR = ':'

/** A sort as one word, to keep it in local storage. */
export function encodeSort(state: SortState | null): string {
  return state ? `${state.key}${SEPARATOR}${state.direction}` : 'none'
}

/** Reads what `encodeSort` wrote; anything else is no sort. */
export function decodeSort(stored: string | null | undefined): SortState | null {
  const at = stored?.lastIndexOf(SEPARATOR) ?? -1
  if (!stored || at < 1)
    return null
  const direction = stored.slice(at + 1)
  return direction === 'asc' || direction === 'desc' ? { key: stored.slice(0, at), direction } : null
}
