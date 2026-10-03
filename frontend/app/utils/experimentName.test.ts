import { describe, expect, it } from 'vitest'
import { shortExperimentName, splitExperimentName } from './experimentName'

describe('splitExperimentName', () => {
  it('strips the batch name and splits the variant', () => {
    expect(splitExperimentName('SSE test · Corrector v2.0 · mistral-medium-2508', 'SSE test')).toEqual({
      segments: ['Corrector v2.0', 'mistral-medium-2508'],
      batch: 'SSE test',
    })
  })

  it('keeps the whole name outside a batch', () => {
    expect(splitExperimentName('My run', null)).toEqual({ segments: ['My run'], batch: null })
    expect(splitExperimentName('A · B')).toEqual({ segments: ['A · B'], batch: null })
  })

  it('keeps the whole name when the batch was renamed', () => {
    expect(splitExperimentName('Old · v1', 'New').segments).toEqual(['Old · v1'])
  })

  it('does not strip a batch name that is only a prefix of a word', () => {
    expect(splitExperimentName('SSE tests · v1', 'SSE test').segments).toEqual(['SSE tests · v1'])
  })

  it('keeps a name that is just the batch prefix', () => {
    expect(splitExperimentName('SSE test · ', 'SSE test').segments).toEqual(['SSE test · '])
  })
})

describe('shortExperimentName', () => {
  it('joins the variant for search', () => {
    expect(shortExperimentName('B · x · y', 'B')).toBe('x · y')
  })
})
