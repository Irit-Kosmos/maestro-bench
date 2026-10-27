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

import type { AgentConfiguration, AgentExecutionSnapshot, AgentInputMapping, FormulaOutput } from '~/types'
import { isMappingComplete } from './utils'

// Aggregator formulas are parsed and checked by the backend (POST /aggregators/check).
// Finding their variables is done here too, so the mapping rows follow the typing without a round trip.

/** Functions a formula can call, as the backend's core.formula defines them */
export const FORMULA_FUNCTIONS: { name: string, signature: string, description: string }[] = [
  { name: 'min', signature: 'min(a, b, …)', description: 'Smallest number; also of a list' },
  { name: 'max', signature: 'max(a, b, …)', description: 'Largest number; also of a list' },
  { name: 'abs', signature: 'abs(x)', description: 'Absolute value' },
  { name: 'round', signature: 'round(x, digits)', description: 'Rounded number; digits is optional' },
  { name: 'mean', signature: 'mean(a, b, …)', description: 'Average; also of a list' },
  { name: 'sum', signature: 'sum(a, b, …)', description: 'Total; also of a list' },
  { name: 'len', signature: 'len(list)', description: 'Number of items of a list' },
  { name: 'clamp', signature: 'clamp(x, low, high)', description: 'x kept between low and high' },
  { name: 'vote', signature: 'vote(a, b, …)', description: 'Most frequent value, also in a list; a tie fails the row' },
]

const FUNCTION_NAMES = new Set(FORMULA_FUNCTIONS.map(f => f.name))
const KEYWORDS = new Set(['and', 'or', 'not', 'if', 'else', 'True', 'False', 'None', 'in', 'is', 'lambda'])

// Strings, numbers (so `1e5` is not read as a variable `e5`), names, then any other character
const TOKEN = /\s+|"(?:[^"\\]|\\.)*"?|'(?:[^'\\]|\\.)*'?|(?:\d+\.?\d*|\.\d+)(?:e[+-]?\d+)?|[a-z_]\w*|./giy

function namesIn(formula: string): string[] {
  const tokens = formula.match(TOKEN) ?? []
  const meaningful = tokens.filter(t => !/^\s+$/.test(t))
  const names: string[] = []
  meaningful.forEach((token, index) => {
    if (!/^[a-z_]\w*$/i.test(token) || KEYWORDS.has(token))
      return
    // A name followed by "(" is a call, not a variable
    if (meaningful[index + 1] === '(')
      return
    if (!names.includes(token))
      names.push(token)
  })
  return names
}

/** Variables to map: names the formulas read that no earlier output defines, in order of appearance */
export function formulaVariables(formulas: readonly FormulaOutput[] | undefined): string[] {
  const variables: string[] = []
  const defined = new Set<string>()
  for (const output of formulas ?? []) {
    for (const name of namesIn(output.formula ?? '')) {
      if (!defined.has(name) && !FUNCTION_NAMES.has(name) && !variables.includes(name))
        variables.push(name)
    }
    if (output.name)
      defined.add(output.name.trim())
  }
  return variables
}

export const DEFAULT_FORMULAS: FormulaOutput[] = [{ name: 'score', formula: '' }]

/** What still blocks an aggregator from running, in words (backend formula errors excluded) */
export function aggregatorIssues(config: AgentConfiguration | undefined): string[] {
  const formulas = config?.formulas ?? []
  const issues: string[] = []
  if (formulas.length === 0)
    issues.push('Add an output')
  if (formulas.some(f => !f.name.trim()))
    issues.push('Name every output')
  const blank = formulas.filter(f => f.name.trim() && !f.formula.trim())
  if (blank.length > 0)
    issues.push(blank.length === 1 ? `Write the formula of ${blank[0]!.name}` : `Write ${blank.length} formulas`)
  const mapped = new Set((config?.input_mappings ?? []).filter(isFormulaMappingComplete).map(m => m.variable))
  const unmapped = formulaVariables(formulas).filter(v => !mapped.has(v))
  if (unmapped.length > 0)
    issues.push(unmapped.length === 1 ? `Map variable ${unmapped[0]}` : `Map ${unmapped.length} variables`)
  return issues
}

/** A formula variable also needs a value when it is fixed: an empty one cannot be computed */
export function isFormulaMappingComplete(mapping: AgentInputMapping | undefined): boolean {
  if (mapping?.source === 'static')
    return !!mapping.staticValue?.trim()
  return isMappingComplete(mapping)
}

/** Short reading of a computed value: 3.6000000001 is 3.6 */
export function formatFormulaValue(value: unknown): string {
  if (Array.isArray(value))
    return `[${value.map(formatFormulaValue).join(', ')}]`
  if (typeof value === 'number')
    return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(6)))
  if (typeof value === 'string')
    return JSON.stringify(value)
  return String(value)
}

/** The formulas an aggregator ran with, as its execution snapshot recorded them */
export function parseSnapshotFormulas(snapshot: Pick<AgentExecutionSnapshot, 'final_formulas'>): FormulaOutput[] {
  if (!snapshot.final_formulas)
    return []
  try {
    const parsed = JSON.parse(snapshot.final_formulas)
    return Array.isArray(parsed) ? parsed : []
  }
  catch {
    return []
  }
}
