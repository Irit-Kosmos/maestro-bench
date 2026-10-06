import { describe, expect, it } from 'vitest'
import { countPlaceholders, findPlaceholders, splitPlaceholders, undeclaredPlaceholders } from './promptPlaceholders'

describe('findPlaceholders', () => {
  it('finds Jinja placeholders whatever the spacing, and tells declared from undeclared', () => {
    const text = 'Hi {{ name }}, {{city}} and {{ other }}'
    const found = findPlaceholders(text, ['name', 'city'])
    expect(found.map(p => [p.name, p.declared])).toEqual([['name', true], ['city', true], ['other', false]])
    expect(text.slice(found[0]!.start, found[0]!.end)).toBe('{{ name }}')
  })

  it('reads the root name of an expression', () => {
    expect(findPlaceholders('{{ answer.text | upper }}', ['answer']).map(p => p.name)).toEqual(['answer'])
  })

  it('ignores braces that are not a name', () => {
    expect(findPlaceholders('{{ }} {{ 1 }} {{ "x" }}', [])).toEqual([])
  })

  it('finds XML slots of declared variables, with both tags', () => {
    const found = findPlaceholders('<answer></answer> and <other></other>', ['answer'])
    expect(found.map(p => [p.name, p.closing])).toEqual([['answer', false], ['answer', true]])
  })

  it('leaves XML slots alone once the text uses {{', () => {
    const found = findPlaceholders('<answer></answer> {{ answer }}', ['answer'])
    expect(found).toHaveLength(1)
    expect(found[0]!.start).toBeGreaterThan(17)
  })
})

describe('splitPlaceholders', () => {
  it('cuts the text without losing a character', () => {
    const text = 'a {{ x }} b {{ y }}'
    const segments = splitPlaceholders(text, ['x'])
    expect(segments.map(s => s.text).join('')).toBe(text)
    expect(segments.map(s => s.placeholder?.name)).toEqual([undefined, 'x', undefined, 'y'])
  })

  it('returns one plain segment when nothing matches', () => {
    expect(splitPlaceholders('plain', ['x'])).toEqual([{ text: 'plain' }])
    expect(splitPlaceholders('', ['x'])).toEqual([])
  })
})

describe('countPlaceholders', () => {
  it('counts uses across texts, an XML slot once', () => {
    const counts = countPlaceholders(['{{ a }} {{ a }}', '<b></b>'], ['a', 'b'])
    expect(counts.get('a')).toBe(2)
    expect(counts.get('b')).toBe(1)
  })

  it('counts undeclared names too', () => {
    expect(countPlaceholders(['{{ z }}'], []).get('z')).toBe(1)
  })
})

describe('undeclaredPlaceholders', () => {
  it('lists each missing name once, in order', () => {
    expect(undeclaredPlaceholders(['{{ b }} {{ a }}', '{{ b }} {{ ok }}'], ['ok'])).toEqual(['b', 'a'])
  })
})
