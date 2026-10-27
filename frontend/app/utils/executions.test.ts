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
import { hasFailures, runsSummary } from './executions'

describe('hasFailures', () => {
  it('counts an execution that failed, or went on with failed rows', () => {
    expect(hasFailures({ status: 'failed', rows_failed: 0 })).toBe(true)
    expect(hasFailures({ status: 'completed', rows_failed: 2 })).toBe(true)
    expect(hasFailures({ status: 'running', rows_failed: 1 })).toBe(true)
  })

  it('leaves out a clean one and a cancelled one, even with failed rows behind it', () => {
    expect(hasFailures({ status: 'completed', rows_failed: 0 })).toBe(false)
    expect(hasFailures({ status: 'cancelled', rows_failed: 3 })).toBe(false)
    expect(hasFailures({ status: 'interrupted', rows_failed: 3 })).toBe(false)
  })
})

describe('runsSummary', () => {
  it('says nothing when all is well', () => {
    expect(runsSummary([{ status: 'completed', rows_failed: 0 }, { status: 'pending' }, { status: 'cancelled', rows_failed: 3 }])).toEqual([])
  })

  it('counts the runs going and the ones that went wrong, failed rows included', () => {
    const parts = runsSummary([
      { status: 'running' },
      { status: 'failed' },
      { status: 'completed', rows_failed: 2 },
      { status: 'completed', rows_failed: 0 },
    ])
    expect(parts.map(part => part.label)).toEqual(['1 running', '2 failed'])
  })
})
