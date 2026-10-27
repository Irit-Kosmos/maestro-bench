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

import type { Person, StudyActivityEvent } from '~/types'
import { ITEM_KINDS } from './studies'
import { parseApiDate } from './utils'

/** Fewest lines a run needs to be folded into one: below it, the lines are short enough to read as they are. */
export const GROUP_MIN = 3
// Lines further apart than this are not the same moment of work
const ADDED_GAP_MS = 10 * 60 * 1000
const COMPLETED_GAP_MS = 24 * 60 * 60 * 1000

type Foldable = Exclude<StudyActivityEvent['type'], 'note'>

export type ActivityRow
  = | { kind: 'event', event: StudyActivityEvent }
    | { kind: 'group', key: string, type: Foldable, actor: Person | null, events: StudyActivityEvent[] }

const time = (event: StudyActivityEvent) => parseApiDate(event.at).getTime()

// Whether `next` carries on the run that ends with `last`. The events come newest first
function carriesOn(last: StudyActivityEvent, next: StudyActivityEvent): boolean {
  if (next.type === 'note' || next.type !== last.type)
    return false
  if (next.type === 'item_added' && next.actor?.id !== last.actor?.id)
    return false
  const gap = Math.abs(time(last) - time(next))
  return gap <= (next.type === 'item_added' ? ADDED_GAP_MS : COMPLETED_GAP_MS)
}

/**
 * Folds the runs of look-alike lines (ten experiments added at once by the same person, a series of runs that
 * completed) into one row each, the way a diff folds the lines nothing happened to. Notes are never folded: they
 * are what the timeline is for. `events` are the newest first, and so are the rows.
 */
export function groupActivity(events: readonly StudyActivityEvent[], min = GROUP_MIN): ActivityRow[] {
  const rows: ActivityRow[] = []
  let run: StudyActivityEvent[] = []

  function flush() {
    if (run.length >= min) {
      const first = run[0]!
      rows.push({
        kind: 'group',
        // The oldest line anchors it, so lines joining the run later don't make it look like another
        key: `${first.type}-${run[run.length - 1]!.at}`,
        type: first.type as Foldable,
        actor: first.actor,
        events: run,
      })
    }
    else {
      rows.push(...run.map((event): ActivityRow => ({ kind: 'event', event })))
    }
    run = []
  }

  for (const event of events) {
    if (event.type === 'note') {
      flush()
      rows.push({ kind: 'event', event })
    }
    else {
      if (run.length && !carriesOn(run[run.length - 1]!, event))
        flush()
      run.push(event)
    }
  }
  flush()
  return rows
}

/** What a folded run says, e.g. "3 experiments and 1 batch". */
export function describeRun(events: readonly StudyActivityEvent[]): string {
  const counts = new Map<string, number>()
  for (const event of events) {
    if (event.item)
      counts.set(event.item.kind, (counts.get(event.item.kind) ?? 0) + 1)
  }
  const parts = [...counts].map(([kind, count]) => {
    const meta = ITEM_KINDS[kind as keyof typeof ITEM_KINDS]
    return `${count} ${(count === 1 ? meta.label : meta.plural).toLowerCase()}`
  })
  return parts.length > 1 ? `${parts.slice(0, -1).join(', ')} and ${parts.at(-1)}` : (parts[0] ?? '')
}
