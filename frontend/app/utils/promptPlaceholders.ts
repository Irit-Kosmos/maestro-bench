export interface Placeholder {
  start: number
  end: number
  name: string
  /** Whether the name is in the declared list (XML slots always are) */
  declared: boolean
  /** The `</name>` half of an XML slot: marked in the text, but not a use of its own */
  closing: boolean
}

export interface PlaceholderSegment {
  text: string
  /** Absent for plain text */
  placeholder?: Placeholder
}

const JINJA = /\{\{-?\s*([A-Z_]\w*)(?:[^\w}][^}]*)?\}\}/gi

const escapeRegExp = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

export function findPlaceholders(text: string, declared: readonly string[]): Placeholder[] {
  const known = new Set(declared)
  const found: Placeholder[] = []

  for (const match of text.matchAll(JINJA)) {
    found.push({
      start: match.index,
      end: match.index + match[0].length,
      name: match[1]!,
      declared: known.has(match[1]!),
      closing: false,
    })
  }

  if (known.size > 0 && !text.includes('{{')) {
    const names = [...known].map(escapeRegExp).join('|')
    for (const match of text.matchAll(new RegExp(`<(/?)(${names})>`, 'g'))) {
      found.push({
        start: match.index,
        end: match.index + match[0].length,
        name: match[2]!,
        declared: true,
        closing: match[1] === '/',
      })
    }
  }

  return found.sort((a, b) => a.start - b.start)
}

/** The text cut into plain runs and placeholders, in order, so the placeholders can be marked up */
export function splitPlaceholders(text: string, declared: readonly string[]): PlaceholderSegment[] {
  const segments: PlaceholderSegment[] = []
  let cursor = 0
  for (const placeholder of findPlaceholders(text, declared)) {
    if (placeholder.start > cursor)
      segments.push({ text: text.slice(cursor, placeholder.start) })
    segments.push({ text: text.slice(placeholder.start, placeholder.end), placeholder })
    cursor = placeholder.end
  }
  if (cursor < text.length)
    segments.push({ text: text.slice(cursor) })
  return segments
}

/** How many times each name is used across the texts, declared or not */
export function countPlaceholders(texts: readonly string[], declared: readonly string[]): Map<string, number> {
  const counts = new Map<string, number>()
  for (const text of texts) {
    for (const placeholder of findPlaceholders(text, declared)) {
      if (!placeholder.closing)
        counts.set(placeholder.name, (counts.get(placeholder.name) ?? 0) + 1)
    }
  }
  return counts
}

/** Names written in the texts and missing from the declared list, in order of appearance */
export function undeclaredPlaceholders(texts: readonly string[], declared: readonly string[]): string[] {
  const names = new Set<string>()
  for (const text of texts) {
    for (const placeholder of findPlaceholders(text, declared)) {
      if (!placeholder.declared)
        names.add(placeholder.name)
    }
  }
  return [...names]
}
