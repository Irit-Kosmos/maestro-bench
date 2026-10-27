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

import type { StepRef } from '~/composables/useAgentPipeline'
import type { Agent, AgentInputMapping } from '~/types'
import { describe, expect, it } from 'vitest'
import { markValues, previewValues, splitRendered } from './promptPreview'

const step = (key: string, label: string): StepRef => ({ key, label, agent: { id: Number.parseInt(key), name: 'Grader' } as Agent })
const row = { answer: 'Bonjour', score: 4, empty: null }

describe('previewValues', () => {
  it('hands the whole row over when nothing is mapped', () => {
    const values = previewValues([], ['answer'], row, [])
    expect(values.answer).toEqual({ text: 'Bonjour', kind: 'value' })
    expect(values.score).toEqual({ text: '4', kind: 'value' })
    expect(values.empty).toEqual({ text: 'None', kind: 'missing' })
  })

  it('reads dataset columns and fixed text', () => {
    const mappings: AgentInputMapping[] = [
      { variable: 'a', source: 'dataset', sourceColumn: 'answer' },
      { variable: 'b', source: 'static', staticValue: 'fixed' },
    ]
    const values = previewValues(mappings, ['a', 'b'], row, [])
    expect(values.a).toEqual({ text: 'Bonjour', kind: 'value' })
    expect(values.b).toEqual({ text: 'fixed', kind: 'value' })
  })

  it('flags a column the row does not have, or that is empty, as missing', () => {
    const mappings: AgentInputMapping[] = [
      { variable: 'a', source: 'dataset', sourceColumn: 'nope' },
      { variable: 'b', source: 'dataset', sourceColumn: 'empty' },
      { variable: 'c', source: 'dataset' },
    ]
    const values = previewValues(mappings, ['a', 'b', 'c'], row, [])
    expect(Object.values(values).map(v => v.kind)).toEqual(['missing', 'missing', 'missing'])
  })

  it('names the step an output comes from, with its path', () => {
    const mappings: AgentInputMapping[] = [
      { variable: 'a', source: 'agent', sourceStep: '2', sourcePath: 'eval.score' },
      { variable: 'b', source: 'agent', sourceStep: '9' },
    ]
    const values = previewValues(mappings, ['a', 'b'], row, [step('2', 'Grader')])
    expect(values.a).toEqual({ text: '‹Grader: eval.score›', kind: 'stand-in' })
    expect(values.b!.kind).toBe('stand-in')
  })

  it('tells the runs of one agent apart, and reads mappings saved with an agent id only', () => {
    const mappings: AgentInputMapping[] = [
      { variable: 'a', source: 'agent', sourceStep: '2#2' },
      { variable: 'b', source: 'agent', sourceAgentId: 2 },
    ]
    const values = previewValues(mappings, ['a', 'b'], row, [step('2', 'Grader'), step('2#2', 'Grader #2')])
    expect(values.a!.text).toBe('‹Grader #2›')
    expect(values.b!.text).toBe('‹Grader›')
  })

  it('stands in for a declared variable that has no mapping', () => {
    const mappings: AgentInputMapping[] = [{ variable: 'a', source: 'static', staticValue: 'x' }]
    expect(previewValues(mappings, ['a', 'b'], row, []).b).toEqual({ text: '‹not mapped›', kind: 'stand-in' })
  })

  it('writes an object value as JSON', () => {
    expect(previewValues([], [], { o: { k: 1 } }, []).o!.text).toBe('{"k":1}')
  })
})

describe('markValues and splitRendered', () => {
  it('lets the values be found again in the rendered text', () => {
    const marked = markValues({ a: { text: 'one', kind: 'value' }, b: { text: '', kind: 'value' } })
    const rendered = `x ${marked.a} y ${marked.b}!`
    expect(splitRendered(rendered)).toEqual([
      { text: 'x ' },
      { text: 'one', variable: 'a' },
      { text: ' y ' },
      { text: '', variable: 'b' },
      { text: '!' },
    ])
  })

  it('drops mark characters a value would carry', () => {
    const marked = markValues({ a: { text: 'a\uE002b', kind: 'value' } })
    expect(splitRendered(marked.a!)).toEqual([{ text: 'ab', variable: 'a' }])
  })

  it('returns plain text as one segment', () => {
    expect(splitRendered('plain')).toEqual([{ text: 'plain' }])
    expect(splitRendered('')).toEqual([])
  })
})
