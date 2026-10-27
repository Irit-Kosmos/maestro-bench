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

import type { FilterSpec } from './filters'
import { describe, expect, it } from 'vitest'
import { buildFilterDefinitions, byOrder, emptyFilterState, matchesSpecs, matchesTerms, searchTerms } from './filters'

interface Item {
  name: string
  kind?: string | null
  tags?: string[]
}

const kind: FilterSpec<Item> = { key: 'kind', label: 'Kind', icon: 'i-ph-tag-bold', value: item => item.kind }
const tags: FilterSpec<Item> = { key: 'tags', label: 'Tags', icon: 'i-ph-tag-bold', multiValued: true, value: item => item.tags }

const items: Item[] = [
  { name: 'a', kind: 'beta', tags: ['x', 'y'] },
  { name: 'b', kind: 'alpha', tags: ['x'] },
  { name: 'c', kind: 'beta' },
  { name: 'd', kind: null },
]

describe('buildFilterDefinitions', () => {
  it('offers the values found in the items, counted and sorted by label', () => {
    const [definition] = buildFilterDefinitions(items, [kind])
    expect(definition!.options.map(option => [option.value, option.count])).toEqual([['alpha', 1], ['beta', 2]])
  })

  it('counts every value of a multi-valued item', () => {
    const [definition] = buildFilterDefinitions(items, [tags])
    expect(definition!.options.map(option => [option.value, option.count])).toEqual([['x', 2], ['y', 1]])
  })

  it('leaves out a filter nobody has a value for', () => {
    expect(buildFilterDefinitions([{ name: 'd', kind: null }], [kind])).toEqual([])
  })

  it('uses the presenter for labels and the comparator for order', () => {
    const spec: FilterSpec<Item> = { ...kind, present: value => ({ label: `Kind ${value}` }), compare: byOrder(['beta', 'alpha']) }
    const [definition] = buildFilterDefinitions(items, [spec])
    expect(definition!.options.map(option => option.label)).toEqual(['Kind beta', 'Kind alpha'])
  })

  it('is a single choice only when asked', () => {
    const [multiple, single] = buildFilterDefinitions(items, [kind, { ...kind, key: 'other', multiple: false }])
    expect([multiple!.multiple, single!.multiple]).toEqual([true, false])
  })
})

describe('byOrder', () => {
  it('puts unlisted values last', () => {
    expect(['z', 'b', 'a'].sort(byOrder(['a', 'b']))).toEqual(['a', 'b', 'z'])
  })
})

describe('matchesSpecs', () => {
  const specs = [kind, tags]
  const state = emptyFilterState(buildFilterDefinitions(items, specs))
  const names = (next: typeof state) => items.filter(item => matchesSpecs(item, specs, next)).map(item => item.name)

  it('lets everything through when no filter is set', () => {
    expect(names(state)).toEqual(['a', 'b', 'c', 'd'])
  })

  it('keeps the items carrying a picked value', () => {
    expect(names({ ...state, kind: { mode: 'include', values: ['beta'] } })).toEqual(['a', 'c'])
  })

  it('combines filters', () => {
    expect(names({ kind: { mode: 'include', values: ['beta'] }, tags: { mode: 'include', values: ['y'] } })).toEqual(['a'])
  })

  it('excludes without dropping the items that have no value', () => {
    expect(names({ ...state, kind: { mode: 'exclude', values: ['beta'] } })).toEqual(['b', 'd'])
  })

  it('requires every value for "all of"', () => {
    expect(names({ ...state, tags: { mode: 'all', values: ['x', 'y'] } })).toEqual(['a'])
  })
})

describe('search', () => {
  it('splits a search into lowercase words', () => {
    expect(searchTerms('  Claude   OPUS ')).toEqual(['claude', 'opus'])
  })

  it('matches every word, in any order, ignoring case', () => {
    expect(matchesTerms('Anthropic claude-opus-4', searchTerms('opus anthropic'))).toBe(true)
    expect(matchesTerms('Anthropic claude-opus-4', searchTerms('opus openai'))).toBe(false)
  })

  it('matches everything when empty', () => {
    expect(matchesTerms('anything', searchTerms('  '))).toBe(true)
  })
})
