import { describe, expect, it } from 'vitest'
import { aggregatorIssues, formatFormulaValue, formulaVariables } from './formula'

describe('formulaVariables', () => {
  it('lists the names to map in order of appearance', () => {
    expect(formulaVariables([
      { name: 'score', formula: 'w1 * langue + w2 * contenu + mean(langue)' },
      { name: 'admis', formula: 'score >= seuil' },
    ])).toEqual(['w1', 'langue', 'w2', 'contenu', 'seuil'])
  })

  it('skips functions, keywords, numbers and strings', () => {
    expect(formulaVariables([
      { name: 'x', formula: '"pass" if round(a, 1) >= 1e5 and not b else \'fail\'' },
    ])).toEqual(['a', 'b'])
  })

  it('treats a function name used without a call as a variable the backend will refuse', () => {
    expect(formulaVariables([{ name: 'x', formula: 'unknown(a)' }])).toEqual(['a'])
  })

  it('reads names defined later as variables', () => {
    expect(formulaVariables([
      { name: 'a', formula: 'b + 1' },
      { name: 'b', formula: '2' },
    ])).toEqual(['b'])
  })
})

describe('aggregatorIssues', () => {
  it('asks for formulas and mappings', () => {
    expect(aggregatorIssues({ formulas: [{ name: 'score', formula: '' }] })).toEqual(['Write the formula of score'])
    expect(aggregatorIssues({
      formulas: [{ name: 'score', formula: 'w * a' }],
      input_mappings: [
        { variable: 'a', source: 'agent', sourceAgentId: 1 },
        { variable: 'w', source: 'static', staticValue: ' ' },
      ],
    })).toEqual(['Map variable w'])
  })

  it('is satisfied by a complete configuration', () => {
    expect(aggregatorIssues({
      formulas: [{ name: 'score', formula: 'w * a' }],
      input_mappings: [
        { variable: 'a', source: 'dataset', sourceColumn: 'gt' },
        { variable: 'w', source: 'static', staticValue: '0.5' },
      ],
    })).toEqual([])
  })
})

describe('formatFormulaValue', () => {
  it('trims float noise and quotes text', () => {
    expect(formatFormulaValue(3.6000000000000005)).toBe('3.6')
    expect(formatFormulaValue(4)).toBe('4')
    expect(formatFormulaValue('a')).toBe('"a"')
    expect(formatFormulaValue(true)).toBe('true')
    expect(formatFormulaValue([0, 0.30000000000000004])).toBe('[0, 0.3]')
  })
})
