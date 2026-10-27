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
import type { StudyActivityEvent } from '~/types'

const props = defineProps<{
  studyId: number
  readonly?: boolean
}>()

const emit = defineEmits<{
  /** A note was edited or deleted, which the rest of the page may show too */
  changed: []
}>()

const { data, pending, error, refresh } = useMyLazyFetch<StudyActivityEvent[]>(
  () => `/studies/${props.studyId}/activity`,
  { key: `study-activity-${props.studyId}`, default: () => [] },
)

const { formatDate, formatRelativeDate } = useUIHelpers()
const events = computed(() => data.value ?? [])

// Runs of look-alike lines are folded; the ones opened stay open when the timeline is read again
const rows = computed(() => groupActivity(events.value))
const open = ref(new Set<string>())
const isOpen = (key: string) => open.value.has(key)
function toggle(key: string) {
  const next = new Set(open.value)
  if (!next.delete(key))
    next.add(key)
  open.value = next
}

// A fold covers a stretch of time: say it on hover (the events are the newest first)
const spanTitle = (run: StudyActivityEvent[]) => `${formatDate(run[run.length - 1]!.at)} → ${formatDate(run[0]!.at)}`

// The page reads the timeline again along with the rest (the journal shows the same notes)
function onNoteChanged() {
  emit('changed')
}
</script>

<template>
  <BaseLoadingState v-if="pending && !events.length" />
  <BaseErrorState v-else-if="error && !events.length" @retry="refresh()" />
  <p v-else-if="!events.length" class="text-sm text-muted">
    Nothing yet. Add experiments, batches or analyses, and write notes: they show up here.
  </p>

  <ol v-else class="flex flex-col gap-3">
    <li v-for="row in rows" :key="row.kind === 'group' ? row.key : `${row.event.type}-${row.event.at}-${row.event.item?.kind}-${row.event.item?.item_id}`">
      <!-- A run of look-alike lines, folded: one line says it, a click opens it -->
      <div v-if="row.kind === 'group'">
        <button
          type="button"
          class="flex w-full cursor-pointer items-center gap-2 rounded px-1 text-start text-xs text-muted outline-none hover:text-toned focus-visible:ring-2 focus-visible:ring-inverted"
          :aria-expanded="isOpen(row.key)"
          @click="toggle(row.key)"
        >
          <UIcon
            name="i-ph-caret-right-bold"
            class="size-3.5 shrink-0 text-dimmed transition-transform ease-(--ease-out) motion-reduce:transition-none"
            :class="isOpen(row.key) ? 'rotate-90 duration-200' : 'duration-150'"
            aria-hidden="true"
          />
          <span class="min-w-0 truncate">
            <template v-if="row.type === 'item_added'">
              <span class="font-medium text-toned">{{ row.actor?.display_name ?? 'Someone' }}</span>
              {{ ' ' }}added {{ describeRun(row.events) }}
            </template>
            <template v-else>
              {{ describeRun(row.events) }} completed
            </template>
          </span>
          <span class="ms-auto shrink-0" :title="spanTitle(row.events)">{{ formatRelativeDate(row.events[0]!.at) }}</span>
        </button>

        <!-- The lines grow out of the fold instead of popping in, so what is below slides rather than jumps. Closing takes 150ms, opening 200ms, and the chevron follows the same clock -->
        <Transition name="reveal">
          <!-- No margin or padding on the first child: it is the one that shrinks, and a track cannot go below them -->
          <div v-if="isOpen(row.key)" class="reveal">
            <div>
              <div class="pt-2">
                <div class="ms-[10.5px] flex flex-col gap-2 border-s border-default ps-3">
                  <StudiesActivityLine v-for="(event, index) in row.events" :key="index" :event="event" />
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <NotesEntry
        v-else-if="row.event.type === 'note' && row.event.note"
        :note="row.event.note"
        :item="row.event.item?.kind === 'study' ? null : row.event.item"
        :readonly="readonly && row.event.note.kind === 'study'"
        compact
        @changed="onNoteChanged"
      />

      <StudiesActivityLine v-else :event="row.event" />
    </li>
  </ol>
</template>
