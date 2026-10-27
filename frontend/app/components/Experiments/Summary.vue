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
// What the experiment will be, and what is still missing. Each row jumps to its section.
interface Row {
  id: 'details' | 'dataset' | 'agents' | 'variations'
  label: string
  /** What is set, or what is missing */
  value: string
  done: boolean
  /** Something is set but needs fixing (as opposed to simply not started) */
  attention?: boolean
}

const props = withDefaults(defineProps<{
  rows: Row[]
  canSubmit: boolean
  submitting: boolean
  /** What the button says: "Create and start" for one experiment, more for a batch */
  submitLabel?: string
  /** Things that will go wrong at run time but do not stop the form from being valid */
  warnings?: string[]
}>(), {
  submitLabel: 'Create and start',
  warnings: () => [],
})

const emit = defineEmits<{
  jump: [id: Row['id']]
  submit: []
  cancel: []
}>()

const hintId = useId()

// The button stays focusable while the form is incomplete, and then does what ⌘↵ does: it takes you to what is missing
function submit() {
  if (props.canSubmit) {
    emit('submit')
    return
  }
  const missing = props.rows.find(row => !row.done)
  if (missing)
    emit('jump', missing.id)
}
</script>

<template>
  <aside aria-labelledby="summary-title" class="rounded-lg border border-default lg:sticky lg:top-0">
    <h2 id="summary-title" class="px-4 pt-4 pb-2 text-sm font-semibold text-highlighted">
      Summary
    </h2>

    <ul class="divide-y divide-default border-y border-default">
      <li v-for="row in rows" :key="row.id">
        <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose. -->
        <button
          type="button"
          class="flex w-full items-start gap-3 px-4 py-3 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
          @click="emit('jump', row.id)"
        >
          <!-- Three shapes, so state never rests on color alone -->
          <UIcon
            :name="row.done ? 'i-ph-check-circle-bold' : row.attention ? 'i-ph-warning-bold' : 'i-ph-circle-bold'"
            class="mt-0.5 size-4 shrink-0"
            :class="row.done ? 'text-success' : row.attention ? 'text-warning' : 'text-muted'"
            aria-hidden="true"
          />
          <span class="min-w-0 flex-1">
            <span class="block text-xs text-muted">{{ row.label }}</span>
            <span
              class="mt-0.5 block text-sm text-pretty"
              :class="row.done ? 'text-highlighted' : row.attention ? 'text-warning' : 'text-muted'"
            >{{ row.value }}</span>
          </span>
        </button>
      </li>
    </ul>

    <ul v-if="warnings.length" class="flex flex-col gap-1.5 px-4 pt-3 text-xs text-warning">
      <li v-for="warning in warnings" :key="warning" class="flex items-start gap-1.5">
        <UIcon name="i-ph-warning-bold" class="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
        <span class="text-pretty">{{ warning }}</span>
      </li>
    </ul>

    <div class="flex flex-col gap-2 p-4">
      <UTooltip :text="submitLabel" :kbds="['meta', 'enter']">
        <UButton
          block
          color="neutral"
          icon="i-ph-play-bold"
          :aria-disabled="!canSubmit"
          :aria-describedby="canSubmit ? undefined : hintId"
          :loading="submitting"
          aria-keyshortcuts="Meta+Enter Control+Enter"
          @click="submit"
        >
          {{ submitLabel }}
        </UButton>
      </UTooltip>
      <p v-if="!canSubmit" :id="hintId" class="text-center text-xs text-muted text-pretty">
        Complete the sections above first. The button takes you to the first one that’s missing.
      </p>
      <UButton block color="neutral" variant="ghost" @click="emit('cancel')">
        Cancel
      </UButton>
    </div>
  </aside>
</template>
