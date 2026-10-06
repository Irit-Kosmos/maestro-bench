import { describe, expect, it } from 'vitest'
import { describeCounts, findStudy, itemCount, itemPath, matchStudies, studyCoverage, studyStatusMeta } from './studies'

const studies = [
  { id: 1, name: 'Prompt v3' },
  { id: 2, name: 'Few-shot prompts' },
  { id: 3, name: 'Model comparison' },
]

describe('findStudy', () => {
  it('ignores case and spacing', () => {
    expect(findStudy(studies, '  prompt   V3 ')?.id).toBe(1)
  })

  it('finds nothing for a blank or unknown name', () => {
    expect(findStudy(studies, '   ')).toBeUndefined()
    expect(findStudy(studies, 'nope')).toBeUndefined()
  })
})

describe('matchStudies', () => {
  it('lists everything by name for an empty query', () => {
    expect(matchStudies(studies, '').map(s => s.id)).toEqual([2, 3, 1])
  })

  it('puts the names that start with the query before those that contain it', () => {
    expect(matchStudies(studies, 'pro').map(s => s.id)).toEqual([1, 2])
    expect(matchStudies(studies, 'prompt').map(s => s.id)).toEqual([1, 2])
    expect(matchStudies(studies, 'comp').map(s => s.id)).toEqual([3])
  })
})

describe('studyCoverage', () => {
  const memberships = [
    { study_id: 1, item_id: 10 },
    { study_id: 1, item_id: 11 },
    { study_id: 2, item_id: 10 },
    { study_id: 2, item_id: 99 },
  ]

  it('counts, per study, how many of the items it holds', () => {
    expect([...studyCoverage(memberships, [10, 11])]).toEqual([[1, 2], [2, 1]])
  })

  it('leaves out studies without any of the items', () => {
    expect(studyCoverage(memberships, [11]).has(2)).toBe(false)
  })
})

describe('describeCounts', () => {
  it('names what is there and nothing else', () => {
    expect(describeCounts({ experiments: 3, batches: 1, analyses: 0 })).toBe('3 experiments · 1 batch')
    expect(describeCounts({ experiments: 1, batches: 2, analyses: 1 })).toBe('1 experiment · 2 batches · 1 analysis')
    expect(describeCounts({ experiments: 0, batches: 0, analyses: 2 })).toBe('2 analyses')
  })

  it('says so when a study is empty', () => {
    expect(describeCounts({ experiments: 0, batches: 0, analyses: 0 })).toBe('Empty')
    expect(itemCount({ experiments: 2, batches: 1, analyses: 1 })).toBe(4)
  })
})

describe('itemPath and studyStatusMeta', () => {
  it('leads to the page of an item', () => {
    expect(itemPath('experiment', 4)).toBe('/experiments/4')
    expect(itemPath('batch', 5)).toBe('/batches/5')
    expect(itemPath('analysis', 6)).toBe('/analyses/6')
    expect(itemPath('study', 7)).toBe('/studies/7')
  })

  it('knows each status, and reads an unknown one as active', () => {
    expect(studyStatusMeta('concluded').label).toBe('Concluded')
    expect(studyStatusMeta('whatever').value).toBe('active')
  })
})
