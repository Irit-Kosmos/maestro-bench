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
import { shortExperimentName, splitExperimentName } from './experimentName'

describe('splitExperimentName', () => {
  it('strips the batch name and splits the variant', () => {
    expect(splitExperimentName('SSE test · Corrector v2.0 · mistral-medium-2508', 'SSE test')).toEqual({
      segments: ['Corrector v2.0', 'mistral-medium-2508'],
      batch: 'SSE test',
    })
  })

  it('keeps the whole name outside a batch', () => {
    expect(splitExperimentName('My run', null)).toEqual({ segments: ['My run'], batch: null })
    expect(splitExperimentName('A · B')).toEqual({ segments: ['A · B'], batch: null })
  })

  it('keeps the whole name when the batch was renamed', () => {
    expect(splitExperimentName('Old · v1', 'New').segments).toEqual(['Old · v1'])
  })

  it('does not strip a batch name that is only a prefix of a word', () => {
    expect(splitExperimentName('SSE tests · v1', 'SSE test').segments).toEqual(['SSE tests · v1'])
  })

  it('keeps a name that is just the batch prefix', () => {
    expect(splitExperimentName('SSE test · ', 'SSE test').segments).toEqual(['SSE test · '])
  })
})

describe('shortExperimentName', () => {
  it('joins the variant for search', () => {
    expect(shortExperimentName('B · x · y', 'B')).toBe('x · y')
  })
})
