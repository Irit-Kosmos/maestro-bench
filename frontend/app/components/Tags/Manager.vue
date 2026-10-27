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
import type { Tag, TagColor } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// Every tag, to rename, recolour or delete. Tags are created where they are used (see TagsInput).
const { tags, pending, updateTag, deleteTag } = useTags()
const { ok, fail } = useStandardToast()
const { canEdit } = useCurrentWorkspace()

function failed(title: string, error: unknown) {
  fail(title, apiErrorMessage(error))
}

async function rename(tag: Tag, event: Event) {
  const input = event.target as HTMLInputElement
  const name = normalizeTagName(input.value)
  if (!name || name === tag.name) {
    input.value = tag.name
    return
  }
  try {
    await updateTag(tag.id, { name })
    ok('Tag renamed')
  }
  catch (error) {
    input.value = tag.name
    failed('Couldn’t rename the tag', error)
  }
}

async function recolor(tag: Tag, color: TagColor) {
  if (color === tag.color)
    return
  try {
    await updateTag(tag.id, { color })
  }
  catch (error) {
    failed('Couldn’t change the colour', error)
  }
}

const toDelete = ref<Tag | null>(null)
const showDeleteDialog = ref(false)
const deleting = ref(false)

function requestDelete(tag: Tag) {
  toDelete.value = tag
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (!toDelete.value)
    return
  deleting.value = true
  try {
    await deleteTag(toDelete.value.id)
    showDeleteDialog.value = false
    ok('Tag deleted')
  }
  catch (error) {
    failed('Couldn’t delete the tag', error)
  }
  finally {
    deleting.value = false
  }
}

const deleteMessage = computed(() => {
  const tag = toDelete.value
  if (!tag)
    return ''
  return `“${tag.name}” is removed from everything it is on.`
})
</script>

<template>
  <div v-if="pending && !tags.length" class="p-4 flex flex-col gap-3">
    <USkeleton v-for="i in 3" :key="i" class="h-4" />
  </div>

  <ul v-else-if="tags.length" class="divide-y divide-default">
    <li v-for="tag in tags" :key="tag.id" class="flex items-center gap-2 h-11 px-4">
      <UPopover :content="{ align: 'start', sideOffset: 6 }">
        <button
          type="button"
          :disabled="!canEdit"
          :aria-label="`Change the colour of ${tag.name}`"
          class="flex size-6 shrink-0 cursor-pointer items-center justify-center rounded-sm outline-none transition-colors duration-150 enabled:hover:bg-elevated focus-visible:bg-elevated focus-visible:ring-2 focus-visible:ring-inverted data-[state=open]:bg-elevated disabled:cursor-default"
        >
          <span class="size-2.5 rounded-full" :class="tagDot(tag.color)" aria-hidden="true" />
        </button>
        <template #content="{ close }">
          <div role="radiogroup" aria-label="Tag colour" class="flex items-center gap-2 p-2.5">
            <button
              v-for="option in TAG_COLORS"
              :key="option"
              type="button"
              role="radio"
              :aria-checked="option === tag.color"
              :aria-label="option"
              :title="option"
              class="size-4 shrink-0 cursor-pointer rounded-full outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-(--ui-text-highlighted) focus-visible:ring-offset-(--ui-bg)"
              :class="[tagDot(option), option === tag.color ? 'ring-2 ring-offset-2 ring-(--ui-text-highlighted) ring-offset-(--ui-bg)' : undefined]"
              @click="recolor(tag, option); close()"
            />
          </div>
        </template>
      </UPopover>

      <input
        :value="tag.name"
        type="text"
        :aria-label="`Name of the tag ${tag.name}`"
        autocomplete="off"
        maxlength="40"
        :readonly="!canEdit"
        class="h-7 min-w-0 flex-1 rounded-sm border border-transparent bg-transparent px-1.5 text-sm text-highlighted outline-none transition-colors duration-150 read-only:cursor-default not-read-only:hover:border-default not-read-only:focus:border-accented focus-visible:ring-2 focus-visible:ring-inverted"
        @change="rename(tag, $event)"
        @keydown.enter="($event.target as HTMLInputElement).blur()"
        @keydown.esc="($event.target as HTMLInputElement).value = tag.name"
      >

      <UButton
        v-if="canEdit"
        icon="i-ph-trash-bold"
        color="neutral"
        variant="ghost"
        size="xs"
        :aria-label="`Delete the tag ${tag.name}`"
        @click="requestDelete(tag)"
      />
    </li>
  </ul>

  <p v-else class="px-4 py-6 text-sm text-muted">
    No tags yet. Add one from a prompt or an analysis.
  </p>

  <BaseConfirmDialog
    v-model:open="showDeleteDialog"
    title="Delete tag?"
    :message="deleteMessage"
    confirm-label="Delete tag"
    variant="error"
    :loading="deleting"
    @confirm="confirmDelete"
  />
</template>
