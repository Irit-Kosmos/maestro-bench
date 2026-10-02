<script setup lang="ts">
import type { DropdownMenuItem } from '@nuxt/ui'
import type { PromptVersion } from '~/types'

// One version, read-only, with what you can do to it. Editing swaps this pane for the form.
const props = defineProps<{
  version: PromptVersion
}>()

const emit = defineEmits<{
  edit: []
  setDefault: []
  toggleActive: []
  delete: []
}>()

const { formatDate } = useUIHelpers()

const variables = computed(() => parseVariables(props.version.variables || ''))
const isEmpty = computed(() => !props.version.system_prompt && !props.version.user_prompt)

const menuItems = computed<DropdownMenuItem[][]>(() => [
  [
    { label: 'Set as default', icon: 'i-lucide-star', disabled: props.version.is_default, onSelect: () => emit('setDefault') },
    {
      label: props.version.is_active ? 'Deactivate' : 'Activate',
      icon: 'i-lucide-power',
      onSelect: () => emit('toggleActive'),
    },
  ],
  [
    { label: 'Delete', icon: 'i-lucide-trash-2', color: 'error', onSelect: () => emit('delete') },
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
        <UButton color="neutral" variant="outline" size="sm" icon="i-lucide-pencil" @click="emit('edit')">
          Edit
          <UKbd value="e" size="sm" />
        </UButton>
        <UDropdownMenu :items="menuItems" :content="{ align: 'end' }">
          <UButton
            icon="i-lucide-ellipsis"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="More actions"
          />
        </UDropdownMenu>
      </div>
    </header>

    <div class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
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
          class="rounded-sm text-primary outline-none hover:underline focus-visible:ring-2 focus-visible:ring-primary"
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
