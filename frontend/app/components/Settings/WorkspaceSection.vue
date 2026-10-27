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
import { apiErrorMessage } from '~/composables/useAnalyses'

const { workspace, archived, can } = useCurrentWorkspace()
const { lifecycle } = useWorkspaceAdmin()
const { workspaces } = useWorkspaces()
const { ok, fail } = useStandardToast()

const isOwner = computed(() => can('owner'))
// An archived workspace is read-only, but its owner can still reopen or delete it
const isOwnerOfArchived = computed(() => workspace.value?.role === 'owner')

const name = ref(workspace.value?.name ?? '')
watch(() => workspace.value?.name, (value) => {
  name.value = value ?? ''
})
const renaming = ref(false)

function failed(error: unknown, title: string) {
  fail(title, apiErrorMessage(error))
}

async function rename() {
  const next = name.value.trim()
  if (!next || next === workspace.value?.name)
    return
  renaming.value = true
  try {
    await lifecycle.rename(next)
    ok('Workspace renamed')
  }
  catch (error) {
    failed(error, 'Couldn’t rename the workspace')
  }
  finally {
    renaming.value = false
  }
}

const showArchive = ref(false)
const busy = ref(false)

async function archive() {
  busy.value = true
  try {
    await lifecycle.archive()
    showArchive.value = false
    ok('Workspace archived')
    // Its keys are gone and its runs stopped: show the page as it now is
    await reloadNuxtApp({ persistState: false })
  }
  catch (error) {
    failed(error, 'Couldn’t archive the workspace')
  }
  finally {
    busy.value = false
  }
}

async function unarchive() {
  busy.value = true
  try {
    await lifecycle.unarchive()
    ok('Workspace reopened')
    await reloadNuxtApp({ persistState: false })
  }
  catch (error) {
    failed(error, 'Couldn’t reopen the workspace')
  }
  finally {
    busy.value = false
  }
}

const showDelete = ref(false)
const confirmation = ref('')
const deleting = ref(false)

async function remove() {
  if (!workspace.value || confirmation.value !== workspace.value.slug)
    return
  deleting.value = true
  try {
    await lifecycle.remove(confirmation.value)
    workspaces.value = null
    await navigateTo('/w', { external: true })
  }
  catch (error) {
    failed(error, 'Couldn’t delete the workspace')
    deleting.value = false
  }
}
</script>

<template>
  <BaseSection v-if="workspace" title="Workspace">
    <div class="flex flex-col divide-y divide-default">
      <form class="flex flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3" @submit.prevent="rename">
        <label for="workspace-name" class="w-full text-sm text-muted sm:w-28 sm:shrink-0">Name</label>
        <UInput id="workspace-name" v-model="name" size="sm" class="min-w-0 flex-1" :disabled="!isOwner" maxlength="80" />
        <UButton
          v-if="isOwner"
          type="submit"
          size="sm"
          color="neutral"
          variant="soft"
          :disabled="!name.trim() || name.trim() === workspace.name"
          :loading="renaming"
        >
          Rename
        </UButton>
      </form>

      <div class="flex items-center gap-3 px-4 py-3">
        <span class="w-28 shrink-0 text-sm text-muted">Identifier</span>
        <code class="min-w-0 truncate text-xs text-toned font-mono" :title="workspace.slug">{{ workspace.slug }}</code>
      </div>

      <div v-if="isOwnerOfArchived" class="flex flex-col gap-3 px-4 py-3">
        <template v-if="!archived">
          <div class="flex items-start gap-3">
            <p class="min-w-0 flex-1 text-xs text-muted text-pretty">
              Archiving makes the workspace read-only: runs in progress stop, and its API keys and invitation links are deleted. You can reopen it later, but the keys must be set again.
            </p>
            <UButton size="sm" color="neutral" variant="outline" icon="i-ph-archive-bold" @click="() => { showArchive = true }">
              Archive
            </UButton>
          </div>
        </template>
        <template v-else>
          <div class="flex items-start gap-3">
            <p class="min-w-0 flex-1 text-xs text-muted text-pretty">
              This workspace is archived and read-only.
            </p>
            <UButton size="sm" color="neutral" variant="outline" :loading="busy" @click="unarchive">
              Reopen
            </UButton>
          </div>
          <div class="flex items-start gap-3">
            <p class="min-w-0 flex-1 text-xs text-muted text-pretty">
              Deleting removes the workspace with its datasets, results, prompts, models, experiments and members. This cannot be undone.
            </p>
            <UButton size="sm" color="error" variant="soft" icon="i-ph-trash-bold" @click="() => { showDelete = true }">
              Delete…
            </UButton>
          </div>
        </template>
      </div>
    </div>

    <BaseConfirmDialog
      v-model:open="showArchive"
      title="Archive workspace"
      :message="`“${workspace.name}” becomes read-only for everyone. Runs in progress are stopped, and the API keys and invitation links are deleted.`"
      confirm-label="Archive"
      :loading="busy"
      @confirm="archive"
    />

    <UModal
      v-model:open="showDelete"
      :title="`Delete “${workspace.name}”`"
      description="Type the workspace identifier to confirm the deletion."
      @after:leave="confirmation = ''"
    >
      <template #content>
        <UCard>
          <template #header>
            <h2 class="text-lg font-semibold text-highlighted">
              Delete “{{ workspace.name }}”
            </h2>
          </template>
          <form class="flex flex-col gap-4" @submit.prevent="remove">
            <p class="text-sm text-toned text-pretty">
              Everything in this workspace is deleted for good. To confirm, type its identifier:
              <code class="font-mono text-highlighted">{{ workspace.slug }}</code>
            </p>
            <UInput v-model="confirmation" autocomplete="off" spellcheck="false" class="w-full" aria-label="Workspace identifier" />
            <div class="flex justify-end gap-3">
              <UButton color="neutral" variant="outline" type="button" @click="() => { showDelete = false }">
                Cancel
              </UButton>
              <UButton type="submit" color="error" :disabled="confirmation !== workspace.slug" :loading="deleting">
                Delete workspace
              </UButton>
            </div>
          </form>
        </UCard>
      </template>
    </UModal>
  </BaseSection>
</template>
