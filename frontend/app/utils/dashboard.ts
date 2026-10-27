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

import type { DashboardRange, DashboardTotals } from '~/types'

export const DASHBOARD_RANGES: readonly { value: DashboardRange, label: string, long: string }[] = [
  { value: '24h', label: '24h', long: '24 hours' },
  { value: '7d', label: '7d', long: '7 days' },
  { value: '30d', label: '30d', long: '30 days' },
  { value: '90d', label: '90d', long: '90 days' },
  { value: 'all', label: 'All', long: 'all time' },
]

export function isDashboardRange(value: unknown): value is DashboardRange {
  return DASHBOARD_RANGES.some(range => range.value === value)
}

export type Change
  = | { kind: 'none' }
    /** Something where there was nothing: no percentage to give */
    | { kind: 'new' }
    | { kind: 'change', percent: number }

/** How much a figure moved since the period before, in percent */
export function relativeChange(current: number, previous: number | null | undefined): Change {
  if (previous == null || (current === 0 && previous === 0))
    return { kind: 'none' }
  if (previous === 0)
    return { kind: 'new' }
  return { kind: 'change', percent: Math.round(((current - previous) / previous) * 100) }
}

/** Share of the rows that failed, 0 to 1; null while no row has gone through */
export function failureRate(totals: Pick<DashboardTotals, 'rows_done' | 'rows_failed'>): number | null {
  return totals.rows_done > 0 ? totals.rows_failed / totals.rows_done : null
}

// "0%", "3.2%", "12%": a rate that is not zero never reads as zero
export function formatRate(rate: number | null): string {
  if (rate === null)
    return '—'
  const percent = rate * 100
  if (percent > 0 && percent < 0.1)
    return '<0.1%'
  return `${percent >= 10 || Number.isInteger(percent) ? Math.round(percent) : percent.toFixed(1)}%`
}
