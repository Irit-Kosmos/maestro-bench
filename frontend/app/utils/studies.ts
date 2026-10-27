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

import type { NoteKind, StudyKind, StudyMembership, StudyStatus } from '~/types'

interface StatusMeta {
  value: StudyStatus
  label: string
  icon: string
  /** Colour of the icon */
  tone: string
  description: string
}

// Each status has its own shape, so it still reads without colour: half-filled (ongoing), check, archive box
export const STUDY_STATUSES: StatusMeta[] = [
  { value: 'active', label: 'Active', icon: 'i-ph-circle-half-bold', tone: 'text-info', description: 'Work is ongoing' },
  { value: 'concluded', label: 'Concluded', icon: 'i-ph-check-circle-bold', tone: 'text-success', description: 'Done, with its findings written down' },
  { value: 'archived', label: 'Archived', icon: 'i-ph-archive-bold', tone: 'text-muted', description: 'Kept for reference, read-only' },
]

export const STUDY_STATUS_ORDER: string[] = STUDY_STATUSES.map(status => status.value)

export function studyStatusMeta(status: string): StatusMeta {
  return STUDY_STATUSES.find(meta => meta.value === status) ?? STUDY_STATUSES[0]!
}

interface KindMeta {
  label: string
  plural: string
  icon: string
  /** Where the pages of this kind live */
  base: string
}

export const ITEM_KINDS: Record<NoteKind, KindMeta> = {
  experiment: { label: 'Experiment', plural: 'Experiments', icon: 'i-ph-flask-bold', base: '/experiments' },
  batch: { label: 'Batch', plural: 'Batches', icon: 'i-ph-arrows-split-bold', base: '/batches' },
  analysis: { label: 'Analysis', plural: 'Analyses', icon: 'i-ph-chart-bar-bold', base: '/analyses' },
  study: { label: 'Study', plural: 'Studies', icon: 'i-ph-notebook-bold', base: '/studies' },
}

/** The kinds a study can gather, in the order they are listed */
export const STUDY_KINDS: StudyKind[] = ['experiment', 'batch', 'analysis']

export function itemPath(kind: NoteKind, id: number): string {
  return `${ITEM_KINDS[kind].base}/${id}`
}

function normalize(name: string): string {
  return name.trim().split(/\s+/).filter(Boolean).join(' ')
}

/** The study with this name, ignoring case and spacing. */
export function findStudy<T extends { name: string }>(studies: readonly T[], name: string): T | undefined {
  const wanted = normalize(name).toLowerCase()
  return wanted ? studies.find(study => normalize(study.name).toLowerCase() === wanted) : undefined
}

/** Studies matching what was typed: the ones that start with it first, then the ones that contain it. All of them for an empty query. */
export function matchStudies<T extends { name: string }>(studies: readonly T[], query: string): T[] {
  const wanted = normalize(query).toLowerCase()
  const byName = (a: T, b: T) => a.name.localeCompare(b.name)
  if (!wanted)
    return [...studies].sort(byName)
  const starts = studies.filter(study => study.name.toLowerCase().startsWith(wanted)).sort(byName)
  const contains = studies.filter(study => !study.name.toLowerCase().startsWith(wanted) && study.name.toLowerCase().includes(wanted)).sort(byName)
  return [...starts, ...contains]
}

/** How many of the items are in each study, by study id. */
export function studyCoverage(memberships: readonly StudyMembership[], itemIds: readonly number[]): Map<number, number> {
  const wanted = new Set(itemIds)
  const counts = new Map<number, number>()
  for (const membership of memberships) {
    if (wanted.has(membership.item_id))
      counts.set(membership.study_id, (counts.get(membership.study_id) ?? 0) + 1)
  }
  return counts
}

/** What a study gathers, in a few words: "3 experiments · 1 batch". */
export function describeCounts(counts: { experiments: number, batches: number, analyses: number }): string {
  const parts = [
    counts.experiments && `${counts.experiments} experiment${counts.experiments === 1 ? '' : 's'}`,
    counts.batches && `${counts.batches} batch${counts.batches === 1 ? '' : 'es'}`,
    counts.analyses && `${counts.analyses} analys${counts.analyses === 1 ? 'is' : 'es'}`,
  ].filter(Boolean)
  return parts.length ? parts.join(' · ') : 'Empty'
}

/** Total items of a study. */
export function itemCount(counts: { experiments: number, batches: number, analyses: number }): number {
  return counts.experiments + counts.batches + counts.analyses
}
