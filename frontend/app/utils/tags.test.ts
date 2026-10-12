import { describe, expect, it } from 'vitest'
import { findTag, matchTags, nextTagColor, normalizeTagName, TAG_COLORS, tagCoverage, tagDot } from './tags'

const tag = (name: string, color: any = 'gray') => ({ name, color })

describe('normalizeTagName', () => {
  it('trims and collapses inner whitespace', () => {
    expect(normalizeTagName('  needs   review \n')).toBe('needs review')
    expect(normalizeTagName('   ')).toBe('')
  })
})

describe('findTag', () => {
  const tags = [tag('Extraction'), tag('paper fig 3')]

  it('ignores case and spacing', () => {
    expect(findTag(tags, ' extraction ')).toBe(tags[0])
    expect(findTag(tags, 'Paper  Fig 3')).toBe(tags[1])
  })

  it('finds nothing for a partial or an empty name', () => {
    expect(findTag(tags, 'extract')).toBeUndefined()
    expect(findTag(tags, '  ')).toBeUndefined()
  })
})

describe('matchTags', () => {
  const tags = [tag('classification'), tag('class-imbalance'), tag('extraction'), tag('subclass')]

  it('lists every tag by name for an empty query', () => {
    expect(matchTags(tags, '').map(t => t.name)).toEqual(['class-imbalance', 'classification', 'extraction', 'subclass'])
  })

  it('puts the tags that start with the query before the ones that contain it', () => {
    expect(matchTags(tags, 'CLASS').map(t => t.name)).toEqual(['class-imbalance', 'classification', 'subclass'])
  })

  it('returns nothing when nothing matches', () => {
    expect(matchTags(tags, 'zzz')).toEqual([])
  })
})

describe('nextTagColor', () => {
  it('starts with the first colour of the palette', () => {
    expect(nextTagColor([])).toBe(TAG_COLORS[0])
  })

  it('suggests the colour used least', () => {
    const used = TAG_COLORS.filter(color => color !== 'gray' && color !== 'teal').map(color => tag(color, color))
    expect(nextTagColor(used)).toBe('teal')
  })

  it('suggests gray only once every other colour is as used', () => {
    const once = TAG_COLORS.filter(color => color !== 'gray').map(color => tag(color, color))
    expect(nextTagColor(once)).toBe('gray')
  })
})

describe('tagDot', () => {
  it('has a dot for every colour of the palette', () => {
    for (const color of TAG_COLORS)
      expect(tagDot(color)).toMatch(/^bg-/)
  })

  it('falls back to gray for an unknown colour', () => {
    expect(tagDot('chartreuse')).toBe(tagDot('gray'))
  })
})

describe('tagCoverage', () => {
  it('counts the items carrying each tag', () => {
    const items = [{ tags: [{ id: 1 }, { id: 2 }] }, { tags: [{ id: 2 }] }, { tags: [] }]
    expect([...tagCoverage(items)]).toEqual([[1, 1], [2, 2]])
  })

  it('has nothing for no items', () => {
    expect(tagCoverage([]).size).toBe(0)
  })
})
