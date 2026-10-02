<script setup lang="ts">
import type { ProviderStatus } from '~/types'

definePageMeta({
  title: 'Settings',
})

useSeoMeta({
  title: 'Settings',
  description: 'LLM providers and backend status.',
})

const { data: providers, pending, refresh } = await useMyLazyFetch<ProviderStatus[]>('/providers')
const { data: health, error: healthError } = await useMyLazyFetch<{ status: string, version: string }>('/health')
const backendUrl = useRuntimeConfig().public.BACK_URL as string

// Same order as everywhere else: by the name people read, not the backend's dict order
const sortedProviders = computed(() => (providers.value ?? []).toSorted((a, b) => compareProviders(a.provider, b.provider)))

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
      <UTooltip text="Check again">
        <UButton
          icon="i-lucide-refresh-cw"
          color="neutral"
          variant="ghost"
          size="sm"
          aria-label="Check again"
          :loading="isRefreshing"
          @click="recheck"
        />
      </UTooltip>
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
        <li v-for="p in sortedProviders" :key="p.provider" class="flex items-center gap-3 h-11 px-4">
          <UIcon
            :name="p.configured ? 'i-lucide-circle-check' : 'i-lucide-circle-dashed'"
            class="size-3.5 shrink-0"
            :class="p.configured ? 'text-success' : 'text-dimmed'"
            aria-hidden="true"
          />
          <UIProviderIcon :provider="p.provider" />
          <span class="w-28 shrink-0 truncate text-sm font-medium text-highlighted">{{ providerLabel(p.provider) }}</span>
          <code class="hidden sm:block min-w-0 truncate text-xs text-muted font-mono">{{ p.env_var }}</code>
          <span class="ms-auto shrink-0 text-xs" :class="p.configured ? 'text-toned' : 'text-muted'">
            {{ p.configured ? 'Ready' : (p.kind === 'url' ? 'URL not set' : 'Key not set') }}
          </span>
        </li>
      </ul>

      <p v-else class="px-4 py-6 text-sm text-muted">
        No providers reported by the backend.
      </p>

      <div class="flex flex-col gap-2 px-4 py-3 border-t border-default text-xs text-muted text-pretty">
        <p>
          Keys and server URLs are read from <code class="font-mono text-toned">backend/.env</code> when the API starts.
          Add one, restart the API, then check again. Ollama needs no key: set its URL, and inside Docker point it at
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
    </BaseSection>

    <BaseSection title="Tags">
      <TagsManager />
    </BaseSection>

    <BaseSection title="Backend">
      <dl class="divide-y divide-default">
        <div class="flex items-center gap-3 h-11 px-4">
          <dt class="text-sm text-muted">
            API
          </dt>
          <dd class="ms-auto min-w-0 truncate text-xs text-toned font-mono">
            {{ backendUrl }}
          </dd>
        </div>
        <div class="flex items-center gap-3 h-11 px-4">
          <dt class="text-sm text-muted">
            Status
          </dt>
          <dd class="ms-auto inline-flex items-center gap-1.5 text-xs text-toned tabular-nums">
            <template v-if="healthError">
              <UIcon name="i-lucide-circle-x" class="size-3.5 text-error" aria-hidden="true" />
              Unreachable
            </template>
            <template v-else-if="health">
              <UIcon name="i-lucide-circle-check" class="size-3.5 text-success" aria-hidden="true" />
              Healthy · v{{ health.version }}
            </template>
            <template v-else>
              —
            </template>
          </dd>
        </div>
      </dl>
    </BaseSection>
  </div>
</template>
