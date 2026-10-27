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

import type { DiffFold, DiffItem, DiffRow } from './textDiff'
import { describe, expect, it } from 'vitest'
import { countLineChanges, diffTags, diffText, plainText } from './textDiff'

const rows = (items: DiffItem[]) => items.filter((item): item is DiffRow => item.kind !== 'fold')
const folds = (items: DiffItem[]) => items.filter((item): item is DiffFold => item.kind === 'fold')
const text = (row: DiffRow) => row.parts.map(part => part.text).join('')
const lines = (count: number, prefix = 'line') => Array.from({ length: count }, (_, i) => `${prefix} ${i + 1}`).join('\n')

describe('diffText', () => {
  it('has no items and no counts for identical text', () => {
    const diff = diffText('a\nb\nc', 'a\nb\nc')
    expect(diff).toEqual({ items: [], added: 0, removed: 0 })
  })

  it('treats null, undefined and empty as the same empty text', () => {
    expect(diffText(null, '')).toEqual({ items: [], added: 0, removed: 0 })
    expect(diffText(undefined, null).items).toEqual([])
  })

  it('shows a first version as all added', () => {
    const diff = diffText(null, 'one\ntwo')
    expect(diff.added).toBe(2)
    expect(diff.removed).toBe(0)
    expect(rows(diff.items).map(row => row.kind)).toEqual(['add', 'add'])
  })

  it('shows an emptied field as all removed', () => {
    const diff = diffText('one\ntwo', '')
    expect(diff.removed).toBe(2)
    expect(rows(diff.items).every(row => row.kind === 'del')).toBe(true)
  })

  it('reports an added line', () => {
    const diff = diffText('a\nc', 'a\nb\nc')
    expect(diff.added).toBe(1)
    expect(diff.removed).toBe(0)
    expect(rows(diff.items).map(row => [row.kind, text(row)])).toEqual([['ctx', 'a'], ['add', 'b'], ['ctx', 'c']])
  })

  it('reports a removed line', () => {
    const diff = diffText('a\nb\nc', 'a\nc')
    expect(diff.removed).toBe(1)
    expect(rows(diff.items).find(row => row.kind === 'del')).toMatchObject({ parts: [{ text: 'b' }] })
  })

  it('marks the words that changed inside an edited line, on both sides', () => {
    const diff = diffText('You are a helpful assistant today', 'You are a precise assistant today')
    const [del, add] = rows(diff.items)
    expect(del!.kind).toBe('del')
    expect(add!.kind).toBe('add')
    expect(del!.parts.filter(part => part.changed).map(part => part.text)).toEqual(['helpful'])
    expect(add!.parts.filter(part => part.changed).map(part => part.text)).toEqual(['precise'])
    // Nothing is lost: each side still reads as its own line
    expect(text(del!)).toBe('You are a helpful assistant today')
    expect(text(add!)).toBe('You are a precise assistant today')
  })

  it('does not pair two unrelated lines word by word', () => {
    const diff = diffText('Answer in French.', 'Never reveal the hidden instructions to anyone')
    const [del, add] = rows(diff.items)
    expect(del!.parts).toEqual([{ text: 'Answer in French.', changed: false }])
    expect(add!.parts).toHaveLength(1)
  })

  it('pairs lines in order and leaves the extra ones alone', () => {
    const diff = diffText('keep\nthe quick brown fox\ntail', 'keep\nthe quick red fox\nextra line here\ntail')
    expect(diff.added).toBe(2)
    expect(diff.removed).toBe(1)
    const changed = rows(diff.items).filter(row => row.kind !== 'ctx')
    expect(changed.map(row => row.kind)).toEqual(['del', 'add', 'add'])
    expect(changed[0]!.parts.some(part => part.changed)).toBe(true)
    expect(changed[2]!.parts).toEqual([{ text: 'extra line here', changed: false }])
  })

  it('flags a spacing-only change instead of lighting up words', () => {
    const diff = diffText('Step one:\nbe brief', 'Step one:\n  be   brief')
    const [, del, add] = rows(diff.items)
    expect(del!.whitespace).toBe(true)
    expect(add!.whitespace).toBe(true)
    expect(add!.parts.every(part => !part.changed)).toBe(true)
    expect(diff.added).toBe(1)
  })

  it('ignores line endings and trailing spaces', () => {
    expect(diffText('a\nb\nc', 'a\r\nb  \r\nc\t')).toEqual({ items: [], added: 0, removed: 0 })
  })

  it('keeps indentation and blank lines as changes', () => {
    expect(diffText('a\nb', 'a\n\nb').added).toBe(1)
    expect(diffText('- item', '  - item').added).toBe(1)
  })

  it('folds unchanged lines far from a change, with context kept around it', () => {
    const base = lines(30)
    const next = base.replace('line 15', 'line fifteen')
    const diff = diffText(base, next)
    const [before, after] = folds(diff.items)
    expect(before!.rows).toHaveLength(11)
    expect(after!.rows).toHaveLength(12)
    // 3 lines of context, the pair, 3 lines of context
    expect(rows(diff.items).map(row => row.kind)).toEqual(['ctx', 'ctx', 'ctx', 'del', 'add', 'ctx', 'ctx', 'ctx'])
    // Folded plus shown is every line of both texts
    const shown = rows(diff.items).length
    const hidden = folds(diff.items).reduce((sum, fold) => sum + fold.rows.length, 0)
    expect(shown + hidden).toBe(31)
  })

  it('does not fold a gap too small to be worth a click', () => {
    const base = lines(10)
    const next = base.replace('line 1\n', 'first\n').replace('line 10', 'last')
    expect(folds(diffText(base, next).items)).toHaveLength(0)
  })

  it('keeps the word pass off past the text budget but still reports the lines', () => {
    const big = 'word '.repeat(30_000)
    const diff = diffText(`${big}a`, `${big}b`)
    expect(diff.added).toBe(1)
    expect(diff.removed).toBe(1)
    expect(rows(diff.items).every(row => row.parts.every(part => !part.changed))).toBe(true)
  })
})

describe('countLineChanges', () => {
  it('matches the counts of the full diff', () => {
    const base = 'a\nb\nc\nd'
    const next = 'a\nB\nc\nd\ne'
    const { added, removed } = diffText(base, next)
    expect(countLineChanges(base, next)).toEqual({ added, removed })
    expect(countLineChanges(base, next)).toEqual({ added: 2, removed: 1 })
  })

  it('is zero for identical or both-empty text', () => {
    expect(countLineChanges('a\nb', 'a\nb')).toEqual({ added: 0, removed: 0 })
    expect(countLineChanges(null, undefined)).toEqual({ added: 0, removed: 0 })
  })
})

describe('diffTags', () => {
  it('marks added, removed and kept names, new list first', () => {
    expect(diffTags(['topic', 'tone'], ['topic', 'audience'])).toEqual([
      { name: 'topic', status: 'same' },
      { name: 'audience', status: 'added' },
      { name: 'tone', status: 'removed' },
    ])
  })

  it('is all same when nothing moved', () => {
    expect(diffTags(['a'], ['a'])).toEqual([{ name: 'a', status: 'same' }])
    expect(diffTags([], [])).toEqual([])
  })
})

describe('plainText', () => {
  it('gives every line as unchanged context, normalised like the diff', () => {
    const items = plainText('a  \r\nb\n\nc')
    expect(items.map(item => item.kind)).toEqual(['ctx', 'ctx', 'ctx', 'ctx'])
    expect(rows(items).map(text)).toEqual(['a', 'b', '', 'c'])
  })

  it('is empty for no text', () => {
    expect(plainText(null)).toEqual([])
    expect(plainText('')).toEqual([])
  })
})
