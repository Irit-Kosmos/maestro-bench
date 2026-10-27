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
import type { ProviderStatus } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

definePageMeta({
  title: 'Settings',
})

useSeoMeta({
  title: 'Settings',
  description: 'Members, LLM providers and backend status.',
})

const { can } = useCurrentWorkspace()
const { keys } = useWorkspaceAdmin()
const { ok, fail } = useStandardToast()

const { data: providers, pending, error: providersError, refresh } = await useMyLazyFetch<ProviderStatus[]>('/providers')
const { data: health, error: healthError } = await useMyLazyFetch<{ status: string, version: string }>('/health')
const backendUrl = useRuntimeConfig().public.BACK_URL as string

// The page scrolls inside <main>, out of the router's reach: jump to `#members` (and co.) by hand
const route = useRoute()
watch(() => route.hash, async (hash) => {
  if (!hash)
    return
  await nextTick()
  document.getElementById(hash.slice(1))?.scrollIntoView({ block: 'start' })
}, { immediate: true, flush: 'post' })

// Same order as everywhere else: by the name people read, not the backend's dict order
const sortedProviders = computed(() => (providers.value ?? []).toSorted((a, b) => compareProviders(a.provider, b.provider)))

const canManageKeys = computed(() => can('owner'))
// The instance cannot encrypt keys (no ENCRYPTION_KEY): say so to the people who could set one
const keysUnavailable = computed(() =>
  canManageKeys.value && !(providers.value ?? []).some(p => p.can_store_key),
)

const keyTarget = ref<ProviderStatus | null>(null)
const showKeyModal = ref(false)
function editKey(provider: ProviderStatus) {
  keyTarget.value = provider
  showKeyModal.value = true
}

const keyToRemove = ref<ProviderStatus | null>(null)
const removingKey = ref(false)
async function removeKey() {
  if (!keyToRemove.value)
    return
  removingKey.value = true
  try {
    const label = providerLabel(keyToRemove.value.provider)
    await keys.remove(keyToRemove.value.provider)
    keyToRemove.value = null
    ok(`${label} key removed`)
    await refresh()
  }
  catch (error) {
    fail('Couldn’t remove the key', apiErrorMessage(error))
  }
  finally {
    removingKey.value = false
  }
}

// The visible button text with the provider appended: the same word is repeated on every row
function keyActionLabel(p: ProviderStatus): string {
  const name = providerLabel(p.provider)
  return p.source === 'workspace' ? `Replace ${name} key` : `Set key for ${name}`
}

function statusText(p: ProviderStatus): string {
  if (p.source === 'workspace')
    return `Workspace key ····${p.key_hint ?? ''}`
  if (p.source === 'instance')
    return p.kind === 'url' ? 'Instance URL' : 'Instance key'
  return p.kind === 'url' ? 'URL not set' : 'Key not set'
}

const readyCount = computed(() => (providers.value ?? []).filter(p => p.configured).length)

// Keys are read when the API starts, so a refresh is how you check a restart took effect
const isRefreshing = ref(false)
async function recheck() {
  isRefreshing.value = true
  try {
    await refresh()
  }
  finally {
    isRefreshing.value = false
  }
}
</script>

<template>
  <div class="flex flex-col gap-6 max-w-3xl">
    <AppPageActions>
      <UButton
        data-tooltip="Check again"
        icon="i-ph-arrows-clockwise-bold"
        color="neutral"
        variant="ghost"
        size="sm"
        aria-label="Check again"
        :loading="isRefreshing"
        @click="recheck"
      />
    </AppPageActions>

    <BaseSection title="LLM providers">
      <template #meta>
        <span v-if="providers?.length" class="text-xs text-muted tabular-nums">
          {{ readyCount }} of {{ providers.length }} ready
        </span>
      </template>

      <div v-if="pending && !providers" class="p-4 flex flex-col gap-3">
        <USkeleton v-for="i in 4" :key="i" class="h-4" />
      </div>

      <ul v-else-if="providers?.length" class="divide-y divide-default">
        <li v-for="p in sortedProviders" :key="p.provider" class="flex flex-wrap items-center gap-x-3 gap-y-1 min-h-11 px-4 py-2 sm:h-11 sm:flex-nowrap sm:py-0">
          <UIcon
            :name="p.configured ? 'i-ph-check-circle-bold' : 'i-ph-circle-dashed-bold'"
            class="size-3.5 shrink-0"
            :class="p.configured ? 'text-success' : 'text-dimmed'"
            aria-hidden="true"
          />
          <UIProviderIcon :provider="p.provider" />
          <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted sm:w-28 sm:flex-none">{{ providerLabel(p.provider) }}</span>
          <code class="hidden sm:block min-w-0 truncate text-xs text-muted font-mono">{{ p.env_var }}</code>
          <!-- Below sm the status and the buttons take a line of their own -->
          <div class="flex items-center gap-3 max-sm:w-full max-sm:justify-end sm:ms-auto">
            <span class="shrink-0 text-xs max-sm:me-auto" :class="p.configured ? 'text-toned' : 'text-muted'">
              {{ statusText(p) }}
            </span>
            <template v-if="canManageKeys && p.kind === 'key'">
              <UButton
                v-if="p.can_store_key"
                size="xs"
                color="neutral"
                variant="ghost"
                :aria-label="keyActionLabel(p)"
                @click="editKey(p)"
              >
                {{ p.source === 'workspace' ? 'Replace' : 'Set key' }}
              </UButton>
              <UTooltip v-if="p.source === 'workspace'" text="Remove the workspace key">
                <UButton
                  icon="i-ph-trash-bold"
                  size="xs"
                  color="neutral"
                  variant="ghost"
                  :aria-label="`Remove the ${providerLabel(p.provider)} key`"
                  @click="() => { keyToRemove = p }"
                />
              </UTooltip>
            </template>
          </div>
        </li>
      </ul>

      <div v-else-if="providersError" class="flex items-center gap-3 px-4 py-6 text-sm text-muted">
        <span>Couldn’t load the providers.</span>
        <UButton size="xs" color="neutral" variant="outline" icon="i-ph-arrow-clockwise-bold" @click="() => { refresh() }">
          Try again
        </UButton>
      </div>

      <p v-else class="px-4 py-6 text-sm text-muted">
        No providers reported by the backend.
      </p>

      <div class="flex flex-col gap-2 px-4 py-3 border-t border-default text-xs text-muted text-pretty">
        <p>
          A provider is called with this workspace’s own key when it has one, else with the instance’s.
          <template v-if="!canManageKeys">
            Only owners can add or replace keys.
          </template>
        </p>
        <p v-if="keysUnavailable">
          This instance cannot store workspace keys: ask its administrator to set
          <code class="font-mono text-toned">ENCRYPTION_KEY</code>.
        </p>

        <!-- Operating the instance: of no use to anyone who only works in the workspace -->
        <details v-if="canManageKeys" class="group">
          <summary class="cursor-pointer select-none rounded-sm text-muted outline-none hover:text-toned focus-visible:text-toned focus-visible:ring-2 focus-visible:ring-inverted">
            Self-hosting notes
          </summary>
          <div class="mt-2 flex flex-col gap-2">
            <p>
              The instance’s keys are read from
              <code class="font-mono text-toned">backend/.env</code> when the API starts. Ollama needs no key: its URL is set for the
              whole instance, and inside Docker it points at
              <code class="font-mono text-toned">host.docker.internal</code>.
            </p>
            <p>
              Need another provider?
              <a
                href="https://docs.litellm.ai/docs/providers"
                target="_blank"
                rel="noopener"
                class="text-toned underline underline-offset-2 hover:text-highlighted"
              >LiteLLM supports many more</a>.
              Add it to <code class="font-mono text-toned">SUPPORTED_PROVIDERS</code> in
              <code class="font-mono text-toned">backend/core/llm.py</code>.
            </p>
          </div>
        </details>
      </div>
    </BaseSection>

    <SettingsMembersSection />

    <BaseSection title="Tags">
      <TagsManager />
    </BaseSection>

    <SettingsWorkspaceSection />

    <BaseSection v-if="canManageKeys" title="Backend">
      <dl class="divide-y divide-default">
        <div class="flex items-center gap-3 h-11 px-4">
          <dt class="text-sm text-muted">
            API
          </dt>
          <dd class="ms-auto min-w-0 truncate text-xs text-toned font-mono" :title="backendUrl">
            {{ backendUrl }}
          </dd>
        </div>
        <div class="flex items-center gap-3 h-11 px-4">
          <dt class="text-sm text-muted">
            Status
          </dt>
          <dd class="ms-auto inline-flex items-center gap-1.5 text-xs text-toned tabular-nums">
            <template v-if="healthError">
              <UIcon name="i-ph-x-circle-bold" class="size-3.5 text-error" aria-hidden="true" />
              Unreachable
            </template>
            <template v-else-if="health">
              <UIcon name="i-ph-check-circle-bold" class="size-3.5 text-success" aria-hidden="true" />
              Healthy · v{{ health.version }}
            </template>
            <template v-else>
              —
            </template>
          </dd>
        </div>
      </dl>
    </BaseSection>

    <SettingsProviderKeyModal v-model:open="showKeyModal" :provider="keyTarget" @saved="() => refresh()" />

    <BaseConfirmDialog
      :open="!!keyToRemove"
      title="Remove the workspace key"
      :message="`${keyToRemove ? providerLabel(keyToRemove.provider) : ''} will use the instance’s key again, if there is one.`"
      confirm-label="Remove"
      variant="error"
      :loading="removingKey"
      @update:open="(value: boolean) => { if (!value) keyToRemove = null }"
      @confirm="removeKey"
    />
  </div>
</template>
