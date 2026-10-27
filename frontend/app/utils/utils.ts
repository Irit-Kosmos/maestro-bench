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

import type { AgentInputMapping } from '~/types'
import { mappingSource } from './steps'

// Helper function to parse variables string to array
export function parseVariables(variablesString: string): string[] {
  if (!variablesString)
    return []
  try {
    const parsed = JSON.parse(variablesString)
    return Array.isArray(parsed) ? parsed : []
  }
  catch (error) {
    console.warn('Failed to parse variables:', error)
    return []
  }
}

// Variable names of a prompt version ("variables" is a JSON array, or an object keyed by name)
export function parsePromptVariables(variablesJson: string | null | undefined): string[] {
  if (!variablesJson)
    return []
  try {
    const parsed = JSON.parse(variablesJson)
    if (Array.isArray(parsed))
      return parsed
    if (typeof parsed === 'object' && parsed !== null)
      return Object.keys(parsed)
    return []
  }
  catch {
    return []
  }
}

// A mapping only counts once its source is fully chosen (a column, an agent or some text)
export function isMappingComplete(mapping: AgentInputMapping | undefined): boolean {
  if (!mapping)
    return false
  if (mapping.source === 'dataset')
    return !!mapping.sourceColumn
  if (mapping.source === 'agent')
    return mappingSource(mapping) !== undefined
  return mapping.source === 'static'
}

// Helper function to stringify variables array to string
export function stringifyVariables(variablesArray: string[]): string {
  if (!variablesArray || variablesArray.length === 0)
    return ''
  return JSON.stringify(variablesArray)
}

// Format an analysis metric value (3 decimals, "—" when undefined)
export function formatMetric(value: number | null | undefined): string {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

// Metrics where the best value is the one closest to zero, whatever its sign
const CLOSEST_TO_ZERO_METRICS = new Set(['bias'])

// Rank score of a metric value across runs: the lowest score is the best run
export function metricRankScore(metric: { key: string, lower_is_better: boolean }, value: number): number {
  if (CLOSEST_TO_ZERO_METRICS.has(metric.key))
    return Math.abs(value)
  return metric.lower_is_better ? value : -value
}

// Below this many rows, metrics are too noisy to compare: flag the run instead of hiding it
export const SMALL_SAMPLE_ROWS = 30

export function isSmallSample(rows: number | null | undefined): boolean {
  return typeof rows === 'number' && rows < SMALL_SAMPLE_ROWS
}

// "1 row", "2,273 rows"
export function formatRows(rows: number): string {
  return `${rows.toLocaleString('en-US')} ${rows === 1 ? 'row' : 'rows'}`
}

// The API serializes moments in UTC with an offset ("2026-10-01T13:58:48.414969Z"). A string
// without one, which `new Date()` would read as local time, is taken as UTC.
export function parseApiDate(dateString: string): Date {
  const hasTimeZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(dateString)
  return new Date(hasTimeZone ? dateString : `${dateString.replace(' ', 'T')}Z`)
}

// "$0.42", "$12.30", "<$0.01" for a run too cheap to show, "—" while unknown
export function formatCost(usd: number | null | undefined): string {
  if (usd === null || usd === undefined)
    return '—'
  if (usd > 0 && usd < 0.01)
    return '<$0.01'
  return `$${usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// "$0.0123": the exact cost, for the tooltip next to a rounded `formatCost`
export function formatCostPrecise(usd: number | null | undefined): string | undefined {
  return usd === null || usd === undefined ? undefined : `$${usd.toFixed(4)}`
}

// "12,345": the exact count, for the tooltip next to a compact `formatTokens`
export function formatCount(count: number | null | undefined): string | undefined {
  return count === null || count === undefined ? undefined : count.toLocaleString('en-US')
}

// "842", "12.4k", "3.1M"
export function formatTokens(tokens: number | null | undefined): string {
  if (tokens === null || tokens === undefined)
    return '—'
  return new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 1 }).format(tokens)
}

// "42s", "2m 14s", "1h 05m": a run's length at a glance, never fractions of a second
export function formatElapsed(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || seconds < 0)
    return '—'
  const total = Math.round(seconds)
  if (total < 60)
    return `${total}s`
  const minutes = Math.floor(total / 60)
  if (minutes < 60)
    return `${minutes}m ${String(total % 60).padStart(2, '0')}s`
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`
}
