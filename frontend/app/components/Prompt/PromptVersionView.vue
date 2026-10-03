<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { VersionDiff } from '~/composables/usePromptDiff'
import type { PromptVersion } from '~/types'

// One version, read-only, with what you can do to it. Editing swaps this pane for the form.
// The same pane can show what changed against another version instead of the text itself.
const props = defineProps<{
  version: PromptVersion
  /** Show changes instead of content */
  changes: boolean
  /** Comparing needs at least two versions */
  canCompare: boolean
  /** Version compared against, and the other versions it can be swapped for (newest first) */
  base: PromptVersion | null
  bases: readonly PromptVersion[]
  /** Null until the diff code is loaded */
  diff: VersionDiff | null
}>()

const emit = defineEmits<{
  'update:changes': [value: boolean]
  'selectBase': [id: number]
  'edit': []
  'setDefault': []
  'toggleActive': []
  'delete': []
}>()

const { formatDate } = useUIHelpers()

const variables = computed(() => parseVariables(props.version.variables || ''))
const isEmpty = computed(() => !props.version.system_prompt && !props.version.user_prompt)

const baseItems = computed<DropdownMenuItem[][]>(() => [
  props.bases.map(candidate => ({
    label: candidate.is_default ? `${candidate.version} · Default` : candidate.version,
    type: 'checkbox' as const,
    checked: candidate.id === props.base?.id,
    onSelect: () => emit('selectBase', candidate.id),
  })),
])

// The two ways to read a version; the same segmented control style as a pill, instant on purpose
const segmentClass = 'h-6 rounded-sm px-2.5 text-xs font-medium outline-none focus-visible:ring-2 focus-visible:ring-inverted disabled:pointer-events-none disabled:opacity-50'

const menuItems = computed<DropdownMenuItem[][]>(() => [
  [
    { label: 'Set as default', icon: 'i-ph-star-bold', disabled: props.version.is_default, onSelect: () => emit('setDefault') },
    {
      label: props.version.is_active ? 'Deactivate' : 'Activate',
      icon: 'i-ph-power-bold',
      onSelect: () => emit('toggleActive'),
    },
  ],
  [
    { label: 'Delete', icon: 'i-ph-trash-bold', color: 'error', onSelect: () => emit('delete') },
  ],
])
</script>

<template>
  <article class="flex min-h-0 flex-col">
    <header class="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-default px-4">
      <div class="flex min-w-0 items-center gap-2.5">
        <h2 class="truncate text-sm font-medium text-highlighted">
          {{ version.version }}
        </h2>
        <UBadge v-if="version.is_default" label="Default" color="success" variant="subtle" size="sm" />
        <UBadge v-if="!version.is_active" label="Inactive" color="neutral" variant="subtle" size="sm" />
        <span class="hidden truncate text-xs text-muted sm:block">
          Created {{ formatDate(version.created_at) }}
        </span>
      </div>

      <div class="flex shrink-0 items-center gap-1">
        <div role="group" aria-label="Show" class="me-1 inline-flex rounded-md bg-elevated p-0.5">
          <button
            type="button"
            :class="[segmentClass, changes ? 'text-muted hover:text-highlighted' : 'bg-default text-highlighted shadow-xs']"
            :aria-pressed="!changes"
            @click="emit('update:changes', false)"
          >
            Version
          </button>
          <UTooltip :delay-duration="400" :disabled="!canCompare">
            <button
              type="button"
              :class="[segmentClass, changes ? 'bg-default text-highlighted shadow-xs' : 'text-muted hover:text-highlighted']"
              :aria-pressed="changes"
              :disabled="!canCompare"
              @click="emit('update:changes', true)"
            >
              Changes
            </button>
            <template #content>
              <span class="flex items-center gap-1.5">Compare with another version <UKbd value="d" size="sm" /></span>
            </template>
          </UTooltip>
        </div>
        <UButton color="neutral" variant="soft" size="sm" icon="i-ph-pencil-simple-bold" @click="emit('edit')">
          Edit
          <UKbd value="e" size="sm" />
        </UButton>
        <UDropdownMenu :items="menuItems" :content="{ align: 'end' }">
          <UButton
            icon="i-ph-dots-three-bold"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="More actions"
          />
        </UDropdownMenu>
      </div>
    </header>

    <div
      v-if="changes"
      class="flex h-9 shrink-0 items-center gap-2 border-b border-default px-4 text-xs text-muted"
    >
      Comparing with
      <UDropdownMenu :items="baseItems" :content="{ align: 'start' }">
        <UButton
          color="neutral"
          variant="outline"
          size="xs"
          trailing-icon="i-ph-caret-up-down-bold"
          :label="base?.version ?? 'Pick a version'"
        />
      </UDropdownMenu>
      <BaseDiffStat v-if="diff" :added="diff.added" :removed="diff.removed" class="ms-auto" />
    </div>

    <div v-if="changes" class="min-h-0 flex-1 overflow-y-auto p-4">
      <PromptVersionDiff v-if="base && diff" :key="base.id" :diff="diff" :base-label="base.version" />
      <p v-else-if="!base" class="text-sm text-muted">
        This is the first version, so there is nothing before it. Pick a version above to compare with.
      </p>
    </div>

    <div v-else class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
      <PromptContentDisplay
        v-if="version.system_prompt"
        label="System prompt"
        :content="version.system_prompt"
        :variables="variables"
      />
      <PromptContentDisplay
        v-if="version.user_prompt"
        label="User prompt"
        :content="version.user_prompt"
        :variables="variables"
      />

      <p v-if="isEmpty" class="text-sm text-muted">
        This version has no prompt text yet.
        <button
          type="button"
          class="rounded-sm text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-inverted"
          @click="emit('edit')"
        >
          Write one
        </button>
      </p>

      <PromptVariablesDisplay v-if="variables.length" :variables="version.variables" />

      <PromptContentDisplay
        v-if="version.notes"
        label="Notes"
        :content="version.notes"
        type="text"
      />
    </div>
  </article>
</template>
