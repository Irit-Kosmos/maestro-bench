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
import type { VersionDiff } from '~/composables/usePromptDiff'

// What changed between two versions, field by field. A field that moved is open, apart from the notes,
// which are metadata. One that did not move is a single closed line: open it to read the whole thing.
const props = defineProps<{
  diff: VersionDiff
  /** Name of the version compared against */
  baseLabel: string
}>()

const moved = (field: VersionDiff['fields'][number]) => field.diff.added + field.diff.removed > 0
const variablesMoved = computed(() => props.diff.variables.some(tag => tag.status !== 'same'))

// Only what the reader toggled; everything else follows its default
const toggled = ref<Readonly<Record<string, boolean>>>({})

function isOpen(key: string, byDefault: boolean) {
  return toggled.value[key] ?? byDefault
}

function toggle(key: string, byDefault: boolean) {
  toggled.value = { ...toggled.value, [key]: !isOpen(key, byDefault) }
}

const collapsibleUi = { content: 'data-[state=open]:animate-none data-[state=closed]:animate-none' }

const toggleClass = '-ms-1 flex items-center gap-0.5 rounded-sm px-1 text-xs font-medium text-muted outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted'
</script>

<template>
  <div class="space-y-5">
    <p v-if="diff.identical" class="text-sm text-muted">
      Identical to {{ baseLabel }}.
    </p>

    <template v-for="field in diff.fields" :key="field.key">
      <section v-if="!field.empty">
        <div class="mb-1.5 flex h-6 items-center justify-between gap-2">
          <h3 class="text-xs font-medium">
            <button
              type="button"
              :class="toggleClass"
              :aria-expanded="isOpen(field.key, moved(field) && field.key !== 'notes')"
              @click="toggle(field.key, moved(field) && field.key !== 'notes')"
            >
              <UIcon
                name="i-ph-caret-right-bold"
                class="size-3.5 transition-transform duration-150 ease-out"
                :class="{ 'rotate-90': isOpen(field.key, moved(field) && field.key !== 'notes') }"
                aria-hidden="true"
              />
              {{ field.label }}
              <span v-if="!moved(field)" class="font-normal text-muted">· Unchanged</span>
            </button>
          </h3>
          <BaseDiffStat :added="field.diff.added" :removed="field.diff.removed" />
        </div>
        <!-- The toggle is the button above. A field opens and closes at once, without sliding -->
        <UCollapsible :open="isOpen(field.key, moved(field) && field.key !== 'notes')" :ui="collapsibleUi">
          <template #content>
            <BaseDiffBlock :items="moved(field) ? field.diff.items : field.full" />
          </template>
        </UCollapsible>
      </section>
    </template>

    <section v-if="diff.variables.length">
      <div class="mb-1.5 flex h-6 items-center">
        <h3 class="text-xs font-medium">
          <button
            type="button"
            :class="toggleClass"
            :aria-expanded="isOpen('variables', variablesMoved)"
            @click="toggle('variables', variablesMoved)"
          >
            <UIcon
              name="i-ph-caret-right-bold"
              class="size-3.5 transition-transform duration-150 ease-out"
              :class="{ 'rotate-90': isOpen('variables', variablesMoved) }"
              aria-hidden="true"
            />
            Variables
            <span v-if="!variablesMoved" class="font-normal text-muted">· Unchanged</span>
          </button>
        </h3>
      </div>
      <UCollapsible :open="isOpen('variables', variablesMoved)" :ui="collapsibleUi">
        <template #content>
          <ul class="flex flex-wrap gap-1.5">
            <li v-for="tag in diff.variables" :key="tag.name">
              <UBadge
                :label="tag.status === 'added' ? `+ ${tag.name}` : tag.status === 'removed' ? `− ${tag.name}` : tag.name"
                :color="tag.status === 'added' ? 'success' : tag.status === 'removed' ? 'error' : 'neutral'"
                variant="subtle"
                size="md"
                class="font-mono"
                :class="{ 'line-through': tag.status === 'removed' }"
              />
            </li>
          </ul>
        </template>
      </UCollapsible>
    </section>
  </div>
</template>
