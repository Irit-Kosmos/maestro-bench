import { diffArrays, diffWordsWithSpace } from 'diff'

// Text diffing for prompt versions. Pure functions, no Vue: the composable decides when to run them.
//
// Prompts are prose, so the diff works on lines first (structure, counters) and only goes to words inside
// pairs of lines that really are two states of the same line.

export interface DiffPart {
  text: string
  /** The words that differ inside a modified line; a whole added or removed line has none */
  changed: boolean
}

export interface DiffRow {
  kind: 'ctx' | 'add' | 'del'
  parts: DiffPart[]
  /** Same words, different spacing: marked as such instead of lit up */
  whitespace: boolean
}

/** A run of unchanged lines far from any change, folded until asked for */
export interface DiffFold {
  kind: 'fold'
  rows: DiffRow[]
}

export type DiffItem = DiffRow | DiffFold

export interface TextDiff {
  items: DiffItem[]
  added: number
  removed: number
}

export interface LineCounts {
  added: number
  removed: number
}

export interface TagDiff {
  name: string
  status: 'same' | 'added' | 'removed'
}

/** Unchanged lines kept on each side of a change */
export const CONTEXT_LINES = 3
/** Folding fewer lines than this costs more clicks than it saves */
const MIN_FOLD_LINES = 3
/** Two lines sharing less than this of their text are not "the same line, edited" */
const MIN_SIMILARITY = 0.35
/** Past this much text, or this long a line, the word pass is skipped: lines only */
const WORD_DIFF_TEXT_BUDGET = 100_000
const WORD_DIFF_LINE_BUDGET = 20_000

/** Line endings and trailing spaces are invisible and mostly paste noise; indentation is kept, it can matter */
function toLines(text: string | null | undefined): string[] {
  if (!text)
    return []
  return text.replace(/\r\n?/g, '\n').split('\n').map(line => line.replace(/[ \t]+$/, ''))
}

function collapseSpaces(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(' ')
}

function plainRow(kind: DiffRow['kind'], text: string): DiffRow {
  return { kind, parts: [{ text, changed: false }], whitespace: false }
}

/** Lines changed between two texts: the cheap pass behind the counters, no rows built */
export function countLineChanges(base: string | null | undefined, next: string | null | undefined): LineCounts {
  let added = 0
  let removed = 0
  for (const part of diffArrays(toLines(base), toLines(next))) {
    if (part.added)
      added += part.count ?? part.value.length
    else if (part.removed)
      removed += part.count ?? part.value.length
  }
  return { added, removed }
}

/** Rows for one modified line, with the words that moved marked on each side */
function pairRows(oldLine: string, newLine: string, withWords: boolean): [DiffRow, DiffRow] {
  const del = plainRow('del', oldLine)
  const add = plainRow('add', newLine)

  if (collapseSpaces(oldLine) === collapseSpaces(newLine)) {
    del.whitespace = true
    add.whitespace = true
    return [del, add]
  }
  if (!withWords || oldLine.length > WORD_DIFF_LINE_BUDGET || newLine.length > WORD_DIFF_LINE_BUDGET)
    return [del, add]

  const words = diffWordsWithSpace(oldLine, newLine)
  let kept = 0
  for (const word of words) {
    if (!word.added && !word.removed)
      kept += word.value.length
  }
  // Two unrelated lines would light up as confetti: better as a plain removed line and a plain added one
  if (kept / Math.max(oldLine.length, newLine.length) < MIN_SIMILARITY)
    return [del, add]

  del.parts = words.filter(word => !word.added).map(word => ({ text: word.value, changed: !!word.removed }))
  add.parts = words.filter(word => !word.removed).map(word => ({ text: word.value, changed: !!word.added }))
  return [del, add]
}

/** Every line of both texts as rows, in reading order, before any folding */
function buildRows(base: string[], next: string[], withWords: boolean): DiffRow[] {
  const rows: DiffRow[] = []
  const parts = diffArrays(base, next)

  for (let index = 0; index < parts.length; index++) {
    const part = parts[index]!
    if (!part.added && !part.removed) {
      for (const line of part.value)
        rows.push(plainRow('ctx', line))
      continue
    }

    // A replacement comes out as removed lines then added lines: pair them up, the rest stands alone
    const following = parts[index + 1]
    const removedLines = part.removed ? part.value : []
    const addedLines = part.removed ? (following?.added ? following.value : []) : part.value
    if (part.removed && following?.added)
      index++

    const paired = Math.min(removedLines.length, addedLines.length)
    const dels: DiffRow[] = []
    const adds: DiffRow[] = []
    for (let line = 0; line < paired; line++) {
      const [del, add] = pairRows(removedLines[line]!, addedLines[line]!, withWords)
      dels.push(del)
      adds.push(add)
    }
    for (let line = paired; line < removedLines.length; line++)
      dels.push(plainRow('del', removedLines[line]!))
    for (let line = paired; line < addedLines.length; line++)
      adds.push(plainRow('add', addedLines[line]!))
    rows.push(...dels, ...adds)
  }
  return rows
}

/** Folds unchanged lines that sit more than CONTEXT_LINES away from any change */
function foldContext(rows: DiffRow[]): DiffItem[] {
  const near = Array.from<boolean>({ length: rows.length }).fill(false)
  rows.forEach((row, index) => {
    if (row.kind === 'ctx')
      return
    const from = Math.max(0, index - CONTEXT_LINES)
    const to = Math.min(rows.length - 1, index + CONTEXT_LINES)
    for (let i = from; i <= to; i++)
      near[i] = true
  })

  const items: DiffItem[] = []
  let run: DiffRow[] = []
  const flush = () => {
    if (run.length >= MIN_FOLD_LINES)
      items.push({ kind: 'fold', rows: run })
    else
      items.push(...run)
    run = []
  }
  rows.forEach((row, index) => {
    if (near[index]) {
      flush()
      items.push(row)
    }
    else {
      run.push(row)
    }
  })
  flush()
  return items
}

/** Line diff of two texts, with word marks inside edited lines and the far context folded */
export function diffText(base: string | null | undefined, next: string | null | undefined): TextDiff {
  const baseLines = toLines(base)
  const nextLines = toLines(next)
  const withWords = (base?.length ?? 0) + (next?.length ?? 0) <= WORD_DIFF_TEXT_BUDGET

  const rows = buildRows(baseLines, nextLines, withWords)
  let added = 0
  let removed = 0
  for (const row of rows) {
    if (row.kind === 'add')
      added++
    else if (row.kind === 'del')
      removed++
  }
  // Nothing changed: no items at all, so "identical" is `added + removed === 0`, not a wall of folded context
  return { items: added + removed === 0 ? [] : foldContext(rows), added, removed }
}

/** A text as it stands, every line unchanged and none folded: for fields that did not move but can be opened */
export function plainText(text: string | null | undefined): DiffItem[] {
  return toLines(text).map(line => plainRow('ctx', line))
}

/** Names present in either list, in the order they read: the new list first, then what was dropped */
export function diffTags(base: readonly string[], next: readonly string[]): TagDiff[] {
  const before = new Set(base)
  const after = new Set(next)
  return [
    ...next.map(name => ({ name, status: before.has(name) ? 'same' as const : 'added' as const })),
    ...base.filter(name => !after.has(name)).map(name => ({ name, status: 'removed' as const })),
  ]
}
