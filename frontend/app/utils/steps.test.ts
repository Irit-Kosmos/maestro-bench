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
import { agentIdOfStep, mappingSource, nextInstance, splitStep, stepKey, stepLabel } from './steps'

describe('step keys', () => {
  it('is the agent id for the first run, then numbered', () => {
    expect(stepKey(12)).toBe('12')
    expect(stepKey(12, 2)).toBe('12#2')
  })

  it('tells the agent and the run back', () => {
    expect(splitStep('12')).toEqual({ agentId: 12, instance: 1 })
    expect(splitStep('12#3')).toEqual({ agentId: 12, instance: 3 })
    expect(agentIdOfStep('7#2')).toBe(7)
  })

  it('names the first run like the agent and the others with their number', () => {
    expect(stepLabel('Corrector', 1)).toBe('Corrector')
    expect(stepLabel('Corrector', 2)).toBe('Corrector #2')
  })

  it('takes the first run number that is free', () => {
    expect(nextInstance(12, [])).toBe(1)
    expect(nextInstance(12, ['12'])).toBe(2)
    expect(nextInstance(12, ['12', '12#2', '3#2'])).toBe(3)
    expect(nextInstance(12, ['12#2'])).toBe(1)
  })
})

describe('mappingSource', () => {
  it('reads the step, or the agent of a mapping saved without one', () => {
    expect(mappingSource({ variable: 'a', source: 'agent', sourceStep: '4#2' })).toBe('4#2')
    expect(mappingSource({ variable: 'a', source: 'agent', sourceAgentId: 4 })).toBe('4')
    expect(mappingSource({ variable: 'a', source: 'agent' })).toBeUndefined()
  })
})
