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

import { describe, expect, it } from 'vitest'
import { failureRate, formatRate, isDashboardRange, relativeChange } from './dashboard'

describe('relativeChange', () => {
  it('compares with the period before', () => {
    expect(relativeChange(150, 100)).toEqual({ kind: 'change', percent: 50 })
    expect(relativeChange(50, 100)).toEqual({ kind: 'change', percent: -50 })
    expect(relativeChange(100, 100)).toEqual({ kind: 'change', percent: 0 })
  })

  it('has nothing to say without a period before or without activity in both', () => {
    expect(relativeChange(10, null)).toEqual({ kind: 'none' })
    expect(relativeChange(0, 0)).toEqual({ kind: 'none' })
  })

  it('does not give a percentage when starting from nothing', () => {
    expect(relativeChange(10, 0)).toEqual({ kind: 'new' })
  })

  it('shows a drop to nothing as -100%', () => {
    expect(relativeChange(0, 8)).toEqual({ kind: 'change', percent: -100 })
  })
})

describe('failureRate', () => {
  it('is the failed share of the rows gone through', () => {
    expect(failureRate({ rows_done: 200, rows_failed: 5 })).toBe(0.025)
  })

  it('is unknown while no row has gone through', () => {
    expect(failureRate({ rows_done: 0, rows_failed: 0 })).toBeNull()
  })
})

describe('formatRate', () => {
  it('keeps a decimal below 10% only', () => {
    expect(formatRate(0.032)).toBe('3.2%')
    expect(formatRate(0.124)).toBe('12%')
    expect(formatRate(0)).toBe('0%')
    expect(formatRate(1)).toBe('100%')
  })

  it('never shows a real failure as 0%', () => {
    expect(formatRate(0.0004)).toBe('<0.1%')
  })

  it('shows a dash when unknown', () => {
    expect(formatRate(null)).toBe('—')
  })
})

describe('isDashboardRange', () => {
  it('accepts the ranges the API knows', () => {
    expect(isDashboardRange('30d')).toBe(true)
    expect(isDashboardRange('all')).toBe(true)
    expect(isDashboardRange('1y')).toBe(false)
    expect(isDashboardRange(undefined)).toBe(false)
  })
})
