<!--
  MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
  Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
  Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as published
  by the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.

  SPDX-License-Identifier: AGPL-3.0-or-later
-->

<script setup lang="ts">
import type { Analysis, Batch, NoteKind, Person, Study, Tag } from '~/types'

// Batches, analyses and studies in one feed, the most recently touched first. Two lines each: the
// name, whole, then what kind of thing it is and the study that holds it. A study holds things, a
// tag only describes them, so they read apart: the tags are a chip on the right (the first one,
// then how many more).
const props = defineProps<{
  batches: readonly Batch[]
  analyses: readonly Analysis[]
  studies: readonly Study[]
  loading?: boolean
  /** How many rows to show at most */
  maxRows?: number
}>()

const CHIPS = 1

// Columns line up with their labels, as in the experiments beside. The tags come once the block is
// wide enough to spare them without starving the name (container queries)
const grid = 'grid items-center gap-x-3 px-4 grid-cols-[1.75rem_minmax(0,1fr)_1.25rem_4rem] @md:grid-cols-[1.75rem_minmax(0,1fr)_minmax(0,min(8rem,30%))_1.25rem_4rem]'
const tagsColumn = 'hidden @md:flex'
const head = 'text-xs text-muted truncate'

const { formatDate, formatRelativeDate } = useUIHelpers()
const { memberships: batchStudies } = useStudyMemberships('batch')
const { memberships: analysisStudies } = useStudyMemberships('analysis')

interface Item {
  key: string
  kind: NoteKind
  to: string
  name: string
  at: string
  author: Person | null | undefined
  /** The studies it is in */
  inStudies: Study[]
  tags: readonly Tag[]
}

const studyById = computed(() => new Map(props.studies.map(study => [study.id, study])))

function studiesOf(memberships: readonly { study_id: number, item_id: number }[], id: number) {
  return memberships
    .filter(m => m.item_id === id)
    .map(m => studyById.value.get(m.study_id))
    .filter((study): study is Study => !!study)
}

const items = computed(() => ([
  ...props.batches.map(batch => ({
    key: `batch-${batch.id}`,
    kind: 'batch' as const,
    to: `/batches/${batch.id}`,
    name: batch.name,
    at: batch.created_at,
    author: batch.author,
    inStudies: studiesOf(batchStudies.value, batch.id),
    tags: [],
  })),
  ...props.analyses.map(analysis => ({
    key: `analysis-${analysis.id}`,
    kind: 'analysis' as const,
    to: `/analyses/${analysis.id}`,
    name: analysis.name,
    at: analysis.updated_at,
    author: analysis.author,
    inStudies: studiesOf(analysisStudies.value, analysis.id),
    tags: analysis.tags,
  })),
  // Archived studies are done with: they are not news
  ...props.studies.filter(study => study.status !== 'archived').map(study => ({
    key: `study-${study.id}`,
    kind: 'study' as const,
    to: `/studies/${study.id}`,
    name: study.name,
    at: study.updated_at,
    author: study.author,
    inStudies: [],
    tags: study.tags,
  })),
] as Item[])
  .sort((a, b) => parseApiDate(b.at).getTime() - parseApiDate(a.at).getTime())
  .slice(0, props.maxRows ?? 8)
  .map(item => ({
    ...item,
    chips: item.tags.slice(0, CHIPS),
    more: item.tags.slice(CHIPS).map(tag => tag.name),
  })))
</script>

<template>
  <div class="@container">
    <!-- Column labels: the rows below carry the same information for assistive tech -->
    <div v-if="loading || items.length" class="h-8 border-b border-default" :class="[grid]" aria-hidden="true">
      <span />
      <span :class="head">Name</span>
      <span :class="[head, tagsColumn]">Tags</span>
      <span :class="head" title="Created by">By</span>
      <span class="text-right" :class="[head]">When</span>
    </div>

    <div v-if="loading" class="divide-y divide-default">
      <div v-for="i in 4" :key="i" class="h-12 px-4 flex items-center gap-3">
        <USkeleton class="size-7 rounded-md" />
        <div class="flex flex-col gap-1.5">
          <USkeleton class="h-3.5 w-40" />
          <USkeleton class="h-3 w-24" />
        </div>
      </div>
    </div>

    <ul v-else-if="items.length" class="divide-y divide-default">
      <li v-for="item in items" :key="item.key">
        <!-- Hover is instant on purpose: rows are scanned and hovered constantly -->
        <NuxtLink
          :to="item.to"
          class="h-12 outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
          :class="[grid]"
        >
          <span class="flex size-7 items-center justify-center rounded-md bg-elevated/60" aria-hidden="true">
            <UIcon :name="ITEM_KINDS[item.kind].icon" class="size-3.5 text-muted" />
          </span>

          <span class="flex min-w-0 flex-col">
            <span class="truncate text-sm font-medium text-highlighted" :title="item.name">{{ item.name }}</span>
            <span class="flex min-w-0 items-center gap-1 text-xs text-muted">
              <span class="shrink-0">{{ ITEM_KINDS[item.kind].label }}</span>
              <template v-if="item.inStudies.length">
                <span class="text-dimmed" aria-hidden="true">·</span>
                <span class="flex min-w-0 items-center gap-1" :title="`In ${item.inStudies.map(study => study.name).join(', ')}`">
                  <UIcon :name="ITEM_KINDS.study.icon" class="size-3 shrink-0 text-dimmed" aria-hidden="true" />
                  <span class="sr-only">in study</span>
                  <span class="truncate text-toned">{{ item.inStudies[0]!.name }}</span>
                  <span v-if="item.inStudies.length > 1" class="shrink-0 tabular-nums">+{{ item.inStudies.length - 1 }}</span>
                </span>
              </template>
            </span>
          </span>

          <span class="min-w-0 items-center gap-1" :class="[tagsColumn]">
            <TagsChip v-for="tag in item.chips" :key="tag.id" :tag="tag" shrinkable />
            <span v-if="item.more.length" class="shrink-0 text-xs tabular-nums text-muted" :title="item.more.join(', ')">
              +{{ item.more.length }}<span class="sr-only"> more tags: {{ item.more.join(', ') }}</span>
            </span>
          </span>

          <UIPerson :person="item.author" label="Created by" avatar-only />
          <span class="whitespace-nowrap text-end text-xs text-muted tabular-nums" :title="formatDate(item.at)">
            {{ formatRelativeDate(item.at) }}
          </span>
        </NuxtLink>
      </li>
    </ul>

    <p v-else class="px-4 py-6 text-sm text-muted">
      No batches, analyses or studies yet. Vary an experiment, compare executions, or open a study.
    </p>
  </div>
</template>
