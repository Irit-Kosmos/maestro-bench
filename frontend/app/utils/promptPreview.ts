import type { StepRef } from '~/composables/useAgentPipeline'
import type { AgentInputMapping } from '~/types'
import { mappingSource } from './steps'

// What an agent would send for one dataset row, to preview its prompt. It reads the mappings the way the
// backend does (core/orchestrator.py, `_resolve_agent_context`), except that the output of an earlier agent
// is only known once it ran: a stand-in names it instead.

/** Where a value comes from: the row, something that only exists at run time, or nothing at all */
export type ValueKind = 'value' | 'stand-in' | 'missing'

export interface PreviewValue {
  text: string
  kind: ValueKind
}

// Marks around each value in the rendered text, to tell which part of it came from which variable. They are
// private-use characters: they pass through the template untouched, and the value of a row cannot hold them.
const OPEN = '\uE000'
const SEPARATOR = '\uE001'
const CLOSE = '\uE002'
const MARKS = /[\uE000\uE001\uE002]/g
const MARKED = /\uE000([^\uE001\uE002]*)\uE001([^\uE002]*)\uE002/g

function asText(value: unknown): string {
  if (value === null || value === undefined)
    return 'None'
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

/** The value of each variable, with the row, the mappings and the steps that run before this one */
export function previewValues(
  mappings: readonly AgentInputMapping[] | undefined,
  variables: readonly string[],
  row: Readonly<Record<string, unknown>>,
  upstreamSteps: readonly StepRef[],
): Record<string, PreviewValue> {
  const values: Record<string, PreviewValue> = {}

  // Without mappings the agent gets the whole row
  if (!mappings?.length) {
    for (const [name, value] of Object.entries(row))
      values[name] = { text: asText(value), kind: value === null || value === undefined ? 'missing' : 'value' }
    return values
  }

  for (const mapping of mappings) {
    if (!mapping.variable || !mapping.source)
      continue
    if (mapping.source === 'static') {
      values[mapping.variable] = { text: mapping.staticValue ?? '', kind: 'value' }
    }
    else if (mapping.source === 'dataset') {
      const value = mapping.sourceColumn ? row[mapping.sourceColumn] : undefined
      values[mapping.variable] = { text: asText(value), kind: value === null || value === undefined ? 'missing' : 'value' }
    }
    else {
      const step = upstreamSteps.find(candidate => candidate.key === mappingSource(mapping))
      const path = mapping.sourcePath ? `: ${mapping.sourcePath}` : ''
      values[mapping.variable] = { text: step ? `‹${step.label}${path}›` : '‹no agent chosen›', kind: 'stand-in' }
    }
  }

  // Declared but not mapped: the run would leave it empty, which the preview would not show
  for (const name of variables) {
    if (!(name in values))
      values[name] = { text: '‹not mapped›', kind: 'stand-in' }
  }
  return values
}

/** The values as the render request carries them, each between marks */
export function markValues(values: Readonly<Record<string, PreviewValue>>): Record<string, string> {
  return Object.fromEntries(Object.entries(values).map(([name, { text }]) =>
    [name, `${OPEN}${name}${SEPARATOR}${text.replace(MARKS, '')}${CLOSE}`]))
}

export interface RenderedSegment {
  text: string
  /** The variable the text is the value of; absent for the prompt's own text */
  variable?: string
}

/** A rendered text cut into the prompt's own text and the values that were put into it */
export function splitRendered(rendered: string): RenderedSegment[] {
  const segments: RenderedSegment[] = []
  let cursor = 0
  for (const match of rendered.matchAll(MARKED)) {
    if (match.index > cursor)
      segments.push({ text: rendered.slice(cursor, match.index) })
    segments.push({ text: match[2]!, variable: match[1]! })
    cursor = match.index + match[0].length
  }
  if (cursor < rendered.length)
    segments.push({ text: rendered.slice(cursor) })
  return segments
}
