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

import type { PromptVersion } from '~/types'
import type { DiffItem, LineCounts, TagDiff, TextDiff } from '~/utils/textDiff'

type TextDiffModule = typeof import('~/utils/textDiff')

export interface FieldDiff {
  key: 'system_prompt' | 'user_prompt' | 'notes'
  label: string
  diff: TextDiff
  /** Nothing on either side: not worth a line of its own */
  empty: boolean
  /** The field as it reads now, for opening one that did not change */
  full: DiffItem[]
}

export interface VersionDiff {
  fields: FieldDiff[]
  variables: TagDiff[]
  /** Lines of system and user prompt: what the counters show. Notes and variables are metadata around them. */
  added: number
  removed: number
  identical: boolean
}

const FIELDS: Pick<FieldDiff, 'key' | 'label'>[] = [
  { key: 'system_prompt', label: 'System prompt' },
  { key: 'user_prompt', label: 'User prompt' },
  { key: 'notes', label: 'Notes' },
]

const CACHE_LIMIT = 200
// Versions whose counters are computed per idle slice
const STATS_BATCH = 6

function signature(base: PromptVersion, next: PromptVersion): string {
  return [base, next]
    .flatMap(version => [version.system_prompt, version.user_prompt, version.variables, version.notes])
    .join('\u0001')
}

function whenIdle(task: () => void) {
  if (typeof requestIdleCallback === 'function')
    requestIdleCallback(task, { timeout: 500 })
  else
    setTimeout(task, 16)
}

/**
 * Diffs between prompt versions, computed on the client from what is already loaded: no request, no spinner.
 * The diff code is a separate chunk, fetched once the page is idle (or on first use), and every result is
 * remembered per pair of versions so stepping back and forth through the history costs nothing.
 *
 * @param versions newest first, so the version before one is the next in the list
 * @param selected the version being read
 * @param baseId the version picked to compare with; null means the one before
 */
export function usePromptDiff(
  versions: Ref<readonly PromptVersion[]>,
  selected: Ref<PromptVersion | null>,
  baseId: Ref<number | null>,
) {
  const lib = shallowRef<TextDiffModule | null>(null)
  let loading: Promise<void> | null = null

  function load(): Promise<void> {
    loading ??= import('~/utils/textDiff')
      .then((module) => {
        lib.value = module
      })
      .catch((error) => {
        loading = null
        console.error('Unable to load the diff code', error)
      })
    return loading
  }

  function previousOf(version: PromptVersion): PromptVersion | null {
    const index = versions.value.findIndex(candidate => candidate.id === version.id)
    return index >= 0 ? versions.value[index + 1] ?? null : null
  }

  const base = computed<PromptVersion | null>(() => {
    const current = selected.value
    if (!current)
      return null
    const picked = baseId.value
    const explicit = picked !== null && picked !== current.id
      ? versions.value.find(version => version.id === picked)
      : undefined
    return explicit ?? previousOf(current)
  })

  const cache = new Map<string, { signature: string, diff: VersionDiff }>()

  function compute(module: TextDiffModule, from: PromptVersion, to: PromptVersion): VersionDiff {
    const key = `${from.id}:${to.id}`
    const sig = signature(from, to)
    const hit = cache.get(key)
    if (hit?.signature === sig)
      return hit.diff

    const fields = FIELDS.map(field => ({
      ...field,
      diff: module.diffText(from[field.key], to[field.key]),
      empty: !from[field.key] && !to[field.key],
      full: module.plainText(to[field.key]),
    }))
    const variables = module.diffTags(parseVariables(from.variables || ''), parseVariables(to.variables || ''))
    const [system, user] = fields as [FieldDiff, FieldDiff, FieldDiff]
    const added = system.diff.added + user.diff.added
    const removed = system.diff.removed + user.diff.removed
    const diff: VersionDiff = {
      fields,
      variables,
      added,
      removed,
      identical: fields.every(field => field.diff.added + field.diff.removed === 0)
        && variables.every(tag => tag.status === 'same'),
    }

    if (cache.size >= CACHE_LIMIT)
      cache.clear()
    cache.set(key, { signature: sig, diff })
    return diff
  }

  const diff = computed<VersionDiff | null>(() => {
    const module = lib.value
    const from = base.value
    const to = selected.value
    return module && from && to ? compute(module, from, to) : null
  })

  // Counters for the list: each version against the one before it, lines only, off the critical path
  const stats = shallowRef(new Map<number, LineCounts>())
  const statSignatures = new Map<number, string>()
  let statsRun = 0

  function refreshStats() {
    const module = lib.value
    if (!module)
      return
    const run = ++statsRun
    const list = versions.value
    const pending = list.flatMap((version, index) => {
      const previous = list[index + 1]
      return previous && statSignatures.get(version.id) !== signature(previous, version)
        ? [{ version, previous }]
        : []
    })

    function slice() {
      if (run !== statsRun)
        return
      const next = new Map(stats.value)
      for (const { version, previous } of pending.splice(0, STATS_BATCH)) {
        const system = module!.countLineChanges(previous.system_prompt, version.system_prompt)
        const user = module!.countLineChanges(previous.user_prompt, version.user_prompt)
        next.set(version.id, { added: system.added + user.added, removed: system.removed + user.removed })
        statSignatures.set(version.id, signature(previous, version))
      }
      stats.value = next
      if (pending.length > 0)
        whenIdle(slice)
    }
    if (pending.length > 0)
      whenIdle(slice)
  }

  watch([versions, lib], refreshStats)
  onMounted(() => whenIdle(load))
  onScopeDispose(() => {
    statsRun++
  })

  return { base, diff, stats, load }
}
