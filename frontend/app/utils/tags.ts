import type { Tag, TagColor } from '~/types'

// Dot colour of each tag colour. Mid-scale hues, a step lighter in dark mode, so they read on both surfaces.
// Class names stay literal strings so Tailwind finds them.
const DOTS: Record<TagColor, string> = {
  red: 'bg-red-500 dark:bg-red-400',
  orange: 'bg-orange-500 dark:bg-orange-400',
  amber: 'bg-amber-500 dark:bg-amber-400',
  green: 'bg-green-500 dark:bg-green-400',
  teal: 'bg-teal-500 dark:bg-teal-400',
  blue: 'bg-blue-500 dark:bg-blue-400',
  indigo: 'bg-indigo-500 dark:bg-indigo-400',
  purple: 'bg-purple-500 dark:bg-purple-400',
  pink: 'bg-pink-500 dark:bg-pink-400',
  gray: 'bg-slate-400 dark:bg-slate-500',
}

/** The ten colours a tag can have, in the order they are offered. */
export const TAG_COLORS = Object.keys(DOTS) as TagColor[]

/** Classes that paint the dot of a tag colour; a colour the palette no longer knows reads as gray. */
export function tagDot(color: string): string {
  return DOTS[color as TagColor] ?? DOTS.gray
}

/** Trimmed, with inner whitespace collapsed, like the API does: "  needs   review " is "needs review". */
export function normalizeTagName(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).join(' ')
}

/** The tag with this name, ignoring case and spacing. */
export function findTag<T extends Pick<Tag, 'name'>>(tags: readonly T[], name: string): T | undefined {
  const wanted = normalizeTagName(name).toLowerCase()
  return wanted ? tags.find(tag => tag.name.toLowerCase() === wanted) : undefined
}

/** Tags matching what was typed: the ones that start with it first, then the ones that contain it. All of them for an empty query. */
export function matchTags<T extends Pick<Tag, 'name'>>(tags: readonly T[], query: string): T[] {
  const wanted = normalizeTagName(query).toLowerCase()
  const byName = (a: T, b: T) => a.name.localeCompare(b.name)
  if (!wanted)
    return [...tags].sort(byName)
  const starts = tags.filter(tag => tag.name.toLowerCase().startsWith(wanted)).sort(byName)
  const contains = tags.filter(tag => !tag.name.toLowerCase().startsWith(wanted) && tag.name.toLowerCase().includes(wanted)).sort(byName)
  return [...starts, ...contains]
}

/** The colour to suggest for a new tag: the one used least so far, the first of the palette on a tie. */
export function nextTagColor(tags: readonly Pick<Tag, 'color'>[]): TagColor {
  const used = new Map<string, number>()
  for (const tag of tags)
    used.set(tag.color, (used.get(tag.color) ?? 0) + 1)
  // Gray reads as "no colour", so it is only suggested once everything else is taken as often
  const colors = TAG_COLORS.filter(color => color !== 'gray')
  return [...colors, 'gray' as const].reduce((best, color) => (used.get(color) ?? 0) < (used.get(best) ?? 0) ? color : best)
}
