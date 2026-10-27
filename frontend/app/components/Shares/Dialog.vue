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
import type { Share, ShareKind } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// Makes, shows and withdraws the public link of an item. It stays open until what was asked is done, and says
// why when it is not.
const props = defineProps<{
  kind: ShareKind
  itemId: number
  /** The workspace is archived: a link can be seen and withdrawn, not made */
  archived?: boolean
}>()

const open = defineModel<boolean>('open', { required: true })

const { getShare, createShare, revokeShare, linkOf } = useShares()
const { ok } = useStandardToast()

// What the link gives, in the words of each kind of item
// What a link to this kind of item picks up later, as the item changes
const GROWS: Partial<Record<ShareKind, string>> = {
  batch: ' Experiments added to the batch later are visible too.',
  analysis: ' Executions added to the analysis later are visible too.',
  study: ' Items added to the study later are visible too, with the executions of its analyses.',
}

const SEES: Record<ShareKind, string> = {
  experiment: 'its setup, the prompts and models of each run, the dataset rows it processed with the outputs, and the results of its executions',
  batch: 'its grid of variants, every experiment of the batch, and the results of their executions',
  analysis: 'its settings, its metrics, and the rows of the executions it compares',
  study: 'its description, what it gathers (experiments, batches, analyses) and the results of their executions',
}

const share = ref<Share | null>(null)
const loading = ref(true)
const busy = ref(false)
const error = ref<string | null>(null)
const confirming = ref<'stop' | 'renew' | null>(null)

const link = computed(() => share.value ? linkOf(share.value) : '')

async function load() {
  loading.value = true
  error.value = null
  try {
    share.value = await getShare(props.kind, props.itemId)
  }
  catch (e) {
    error.value = apiErrorMessage(e) ?? 'Couldn’t read the link.'
  }
  finally {
    loading.value = false
  }
}

// Read when it opens, so that a link made or withdrawn elsewhere is what is shown
watch(open, (isOpen) => {
  if (isOpen) {
    confirming.value = null
    load()
  }
}, { immediate: true })

/** Run what was asked; on failure the dialog stays and says why */
async function run(action: () => Promise<void>, failure: string) {
  busy.value = true
  error.value = null
  try {
    await action()
  }
  catch (e) {
    error.value = apiErrorMessage(e) ?? failure
  }
  finally {
    busy.value = false
  }
}

function createLink() {
  return run(async () => {
    share.value = await createShare(props.kind, props.itemId)
    ok('Link created')
  }, 'Couldn’t create the link.')
}

function stopSharing() {
  return run(async () => {
    if (share.value)
      await revokeShare(share.value.id)
    share.value = null
    confirming.value = null
    ok('Sharing stopped', { description: 'The link no longer works.' })
  }, 'Couldn’t stop sharing.')
}

function renewLink() {
  return run(async () => {
    if (share.value)
      await revokeShare(share.value.id)
    // The old link is gone for good, whatever happens next
    share.value = null
    share.value = await createShare(props.kind, props.itemId)
    confirming.value = null
    ok('New link created', { description: 'The old one no longer works.' })
  }, 'Couldn’t make a new link.')
}
</script>

<template>
  <UModal
    v-model:open="open"
    :title="`Share this ${kind}`"
    description="Anyone with the link can read it, without an account."
    :dismissible="!busy"
  >
    <template #body>
      <div v-if="loading" class="flex justify-center py-8">
        <UIcon name="i-ph-spinner-bold" class="size-5 animate-spin text-muted" aria-label="Loading" />
      </div>

      <div v-else class="flex flex-col gap-4">
        <UAlert v-if="error && !confirming" color="error" variant="subtle" icon="i-ph-warning-circle-bold" :description="error" />

        <template v-if="share">
          <div class="flex items-center gap-2">
            <UInput
              :model-value="link"
              readonly
              class="min-w-0 flex-1 font-mono"
              aria-label="Public link"
              @focus="($event.target as HTMLInputElement).select()"
            />
            <UICopyButton :text="link" label="public link" size="md" variant="outline" />
          </div>
        </template>

        <p v-else-if="!error" class="text-sm text-toned text-pretty">
          {{ archived ? 'This workspace is archived: no link can be made in it.' : 'Nobody can open it until you make a link.' }}
        </p>

        <ul class="flex flex-col gap-2 text-sm text-toned">
          <li class="flex gap-2">
            <UIcon name="i-ph-eye-bold" class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
            <span class="text-pretty"><span class="font-medium text-highlighted">They see</span> {{ SEES[kind] }}.</span>
          </li>
          <li class="flex gap-2">
            <UIcon name="i-ph-eye-slash-bold" class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
            <span class="text-pretty"><span class="font-medium text-highlighted">They don’t see</span> your notes, who created it, tags, or anything else in your workspace. They can’t change anything.</span>
          </li>
          <li class="flex gap-2">
            <UIcon name="i-ph-arrows-clockwise-bold" class="mt-0.5 size-4 shrink-0 text-muted" aria-hidden="true" />
            <span class="text-pretty"><span class="font-medium text-highlighted">It stays up to date.</span> If you change it later, they see the change.{{ GROWS[kind] }}</span>
          </li>
        </ul>
      </div>
    </template>

    <template #footer>
      <div class="flex w-full items-center justify-end gap-2">
        <template v-if="share">
          <UButton color="neutral" variant="ghost" :disabled="busy" @click="() => { confirming = 'stop' }">
            Stop sharing
          </UButton>
          <UButton v-if="!archived" color="neutral" variant="outline" icon="i-ph-arrows-counter-clockwise-bold" :disabled="busy" @click="() => { confirming = 'renew' }">
            New link
          </UButton>
        </template>
        <UButton v-else-if="!loading && !archived" color="neutral" icon="i-ph-link-bold" :loading="busy" @click="createLink">
          Create link
        </UButton>
        <UButton color="neutral" variant="outline" :disabled="busy" @click="() => { open = false }">
          Close
        </UButton>
      </div>
    </template>
  </UModal>

  <BaseConfirmDialog
    :open="confirming === 'stop'"
    title="Stop sharing?"
    message="The link stops working at once, for everyone who has it. You can make a new one later."
    confirm-label="Stop sharing"
    variant="warning"
    :loading="busy"
    :error="error"
    @update:open="(value: boolean) => { if (!value) confirming = null }"
    @confirm="stopSharing"
  />

  <BaseConfirmDialog
    :open="confirming === 'renew'"
    title="Make a new link?"
    message="The current link stops working at once. Whoever has it will need the new one."
    confirm-label="Make a new link"
    variant="warning"
    :loading="busy"
    :error="error"
    @update:open="(value: boolean) => { if (!value) confirming = null }"
    @confirm="renewLink"
  />
</template>
