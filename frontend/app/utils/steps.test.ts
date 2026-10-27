import { describe, expect, it } from 'vitest'
import { agentIdOfStep, mappingSource, nextInstance, splitStep, stepKey, stepLabel } from './steps'

describe('step keys', () => {
  it('is the agent id for the first run, then numbered', () => {
    expect(stepKey(12)).toBe('12')
    expect(stepKey(12, 2)).toBe('12#2')
  })

  it('tells the agent and the run back', () => {
    expect(splitStep('12')).toEqual({ agentId: 12, instance: 1 })
    expect(splitStep('12#3')).toEqual({ agentId: 12, instance: 3 })
    expect(agentIdOfStep('7#2')).toBe(7)
  })

  it('names the first run like the agent and the others with their number', () => {
    expect(stepLabel('Corrector', 1)).toBe('Corrector')
    expect(stepLabel('Corrector', 2)).toBe('Corrector #2')
  })

  it('takes the first run number that is free', () => {
    expect(nextInstance(12, [])).toBe(1)
    expect(nextInstance(12, ['12'])).toBe(2)
    expect(nextInstance(12, ['12', '12#2', '3#2'])).toBe(3)
    expect(nextInstance(12, ['12#2'])).toBe(1)
  })
})

describe('mappingSource', () => {
  it('reads the step, or the agent of a mapping saved without one', () => {
    expect(mappingSource({ variable: 'a', source: 'agent', sourceStep: '4#2' })).toBe('4#2')
    expect(mappingSource({ variable: 'a', source: 'agent', sourceAgentId: 4 })).toBe('4')
    expect(mappingSource({ variable: 'a', source: 'agent' })).toBeUndefined()
  })
})
