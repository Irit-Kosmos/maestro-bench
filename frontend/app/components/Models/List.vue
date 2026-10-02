<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { ModelGroup } from '~/composables/useModelFilters'
import type { Model, ProviderStatus } from '~/types'

// The models, one dense row each, under a header per group (provider by default).
// Columns appear as the block gets wider (container queries, so a resized sidebar counts too).
const props = defineProps<{
  groups: readonly ModelGroup[]
  /** Draw a header per group; off for the flat list */
  grouped: boolean
  /** Groups already say which provider a row belongs to; otherwise the row has to */
  showProvider: boolean
  isCollapsed: (key: string) => boolean
  /** Whether the backend has an API key, by canonical provider key */
  providerStatus: Readonly<Record<string, ProviderStatus>>
}>()

const emit = defineEmits<{
  toggleGroup: [key: string]
  edit: [model: Model]
  toggleStatus: [model: Model]
  delete: [model: Model]
}>()

// Without the provider column the block needs less room for each of the others
const layout = computed(() => props.showProvider
  ? {
      grid: 'grid items-center gap-x-4 px-4 grid-cols-[minmax(0,1fr)_2.5rem_2rem] @xl:grid-cols-[minmax(0,1fr)_8rem_2.5rem_2rem] @3xl:grid-cols-[minmax(0,1fr)_8rem_4.5rem_2.5rem_2rem] @4xl:grid-cols-[minmax(0,1fr)_8rem_4.5rem_4rem_2.5rem_2rem]',
      provider: 'hidden @xl:flex',
      context: 'hidden @3xl:block',
      temperature: 'hidden @4xl:block',
    }
  : {
      grid: 'grid items-center gap-x-4 px-4 grid-cols-[minmax(0,1fr)_2.5rem_2rem] @xl:grid-cols-[minmax(0,1fr)_4.5rem_2.5rem_2rem] @3xl:grid-cols-[minmax(0,1fr)_4.5rem_4rem_2.5rem_2rem]',
      provider: 'hidden',
      context: 'hidden @xl:block',
      temperature: 'hidden @3xl:block',
    },
)

const head = 'text-xs text-dimmed truncate'

function menuItems(model: Model): DropdownMenuItem[][] {
  return [
    [
      { label: 'Edit', icon: 'i-lucide-pencil', onSelect: () => emit('edit', model) },
      { label: model.is_active ? 'Deactivate' : 'Activate', icon: 'i-lucide-power', onSelect: () => emit('toggleStatus', model) },
    ],
    [
      { label: 'Delete', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => emit('delete', model) },
    ],
  ]
}

function statusOf(group: ModelGroup) {
  return group.provider ? props.providerStatus[group.provider] : undefined
}

function summary(group: ModelGroup) {
  const inactive = group.models.length - group.activeCount
  return inactive > 0 ? `${group.activeCount} of ${group.models.length} active` : `${group.models.length}`
}
</script>

<template>
  <div class="@container">
    <!-- Column labels: the rows carry the same information for assistive tech -->
    <div class="h-8 border-b border-default bg-muted/60" :class="[layout.grid]" aria-hidden="true">
      <span :class="head">Model</span>
      <span :class="[head, layout.provider]">Provider</span>
      <span class="text-right" :class="[head, layout.context]">Context</span>
      <span class="text-right" :class="[head, layout.temperature]">Temp.</span>
      <span class="text-right" :class="[head]">Active</span>
      <span />
    </div>

    <div class="divide-y divide-default">
      <section
        v-for="group in groups"
        :key="group.key"
        :aria-label="grouped ? group.label : 'Models'"
      >
        <header v-if="grouped" class="flex h-9 items-center gap-2 bg-muted/40 ps-2 pe-4">
          <button
            type="button"
            class="flex h-7 min-w-0 flex-1 items-center gap-2 rounded-md px-2 text-left outline-none hover:bg-elevated/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-primary"
            :aria-expanded="!isCollapsed(group.key)"
            @click="emit('toggleGroup', group.key)"
          >
            <UIcon
              name="i-lucide-chevron-right"
              class="size-4 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none"
              :class="!isCollapsed(group.key) && 'rotate-90'"
              aria-hidden="true"
            />
            <UIProviderIcon v-if="group.provider" :provider="group.provider" class="size-4" />
            <UIcon
              v-else
              :name="group.key === 'active' ? 'i-lucide-circle-check' : 'i-lucide-circle-slash'"
              class="size-4 shrink-0"
              :class="group.key === 'active' ? 'text-success' : 'text-dimmed'"
              aria-hidden="true"
            />
            <span class="truncate text-sm font-medium text-highlighted">{{ group.label }}</span>
            <span class="shrink-0 text-xs text-muted tabular-nums">{{ summary(group) }}</span>
          </button>

          <!-- Can this provider be called? -->
          <UTooltip
            v-if="statusOf(group)"
            :text="statusOf(group)!.configured ? `Key found in ${statusOf(group)!.api_key_env}` : `Set ${statusOf(group)!.api_key_env} to run these models`"
          >
            <NuxtLink
              to="/settings"
              class="inline-flex shrink-0 items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs outline-none hover:bg-elevated/60 focus-visible:outline-2 focus-visible:outline-primary"
              :class="statusOf(group)!.configured ? 'text-muted' : 'text-warning'"
            >
              <UIcon
                :name="statusOf(group)!.configured ? 'i-lucide-key-round' : 'i-lucide-triangle-alert'"
                class="size-3.5"
                aria-hidden="true"
              />
              {{ statusOf(group)!.configured ? 'Key set' : 'No API key' }}
            </NuxtLink>
          </UTooltip>
        </header>

        <ul v-if="!grouped || !isCollapsed(group.key)" class="divide-y divide-default">
          <li
            v-for="model in group.models"
            :key="model.id"
            class="relative hover:bg-elevated/50"
          >
            <div class="h-11" :class="[layout.grid]">
              <!-- The name's button stretches over the row; the switch and menu sit above it -->
              <div class="flex min-w-0 items-baseline gap-2">
                <button
                  type="button"
                  class="min-w-0 max-w-[65%] shrink-0 truncate self-center text-left text-sm font-medium outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-primary"
                  :class="model.is_active ? 'text-highlighted' : 'text-muted'"
                  :aria-label="`Edit ${model.name}`"
                  @click="emit('edit', model)"
                >
                  {{ model.name }}
                </button>
                <span
                  v-if="model.description"
                  class="hidden min-w-0 truncate text-xs text-muted sm:block"
                  :title="model.description"
                >
                  {{ model.description }}
                </span>
              </div>

              <span class="min-w-0 items-center gap-1.5 text-xs text-toned" :class="[layout.provider]">
                <UIProviderIcon :provider="model.provider" />
                <span class="truncate">{{ providerLabel(model.provider) }}</span>
              </span>

              <span
                class="text-right text-xs tabular-nums text-toned"
                :class="layout.context"
                :title="model.max_tokens ? `Context window: ${model.max_tokens.toLocaleString('en-US')} tokens` : undefined"
              >
                {{ model.max_tokens ? formatTokens(model.max_tokens) : '—' }}
              </span>
              <span class="text-right text-xs tabular-nums text-toned" :class="layout.temperature">
                {{ model.default_temperature ?? '—' }}
              </span>

              <span class="relative z-1 flex justify-end">
                <USwitch
                  :model-value="model.is_active"
                  size="xs"
                  :aria-label="`${model.name} is active`"
                  @update:model-value="emit('toggleStatus', model)"
                />
              </span>

              <UDropdownMenu :items="menuItems(model)" :content="{ align: 'end' }">
                <UButton
                  icon="i-lucide-ellipsis"
                  color="neutral"
                  variant="ghost"
                  size="sm"
                  class="relative z-1"
                  :aria-label="`Actions for ${model.name}`"
                />
              </UDropdownMenu>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
