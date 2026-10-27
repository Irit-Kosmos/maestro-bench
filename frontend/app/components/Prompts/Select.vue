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
import type { PromptVersion } from '~/types'

// Picks one prompt version (or several): grouped by prompt, versions nested under their prompt's name,
// searchable by prompt name or version. Inactive versions are hidden, except the ones already chosen
// so an existing setup never breaks. The trigger reads "Prompt name 1.2".
const props = withDefaults(defineProps<{
  promptVersions: readonly PromptVersion[]
  placeholder?: string
  multiple?: boolean
  /** Lets the choice be cleared (the value becomes null) */
  clearable?: boolean
  /** Shown ticked and fixed, labelled "Current setup": the value the others are compared to */
  lockedId?: number | null
  /** Per-version description or disabled state, e.g. to explain why a version can't be picked */
  itemState?: (version: PromptVersion) => { description?: string, disabled?: boolean } | undefined
  searchPlaceholder?: string
}>(), {
  placeholder: 'Choose a prompt version',
  lockedId: null,
  searchPlaceholder: 'Search prompts or versions…',
})

const { formatShortDate } = useUIHelpers()

const model = defineModel<number | number[] | null | undefined>({ default: undefined })

const selectedIds = computed(() => new Set(
  (Array.isArray(model.value) ? model.value : [model.value]).filter((id): id is number => typeof id === 'number'),
))

// Newest first: "1.10" comes after "1.9", which a plain string compare gets wrong
const byVersionDesc = (a: PromptVersion, b: PromptVersion) => b.version.localeCompare(a.version, 'en', { numeric: true })

// Typed loosely: label rows and version rows share one list, which the menu's own typing can't express
const items = computed<any[][]>(() => {
  const byPrompt = new Map<number, { name: string, versions: PromptVersion[] }>()
  for (const v of props.promptVersions) {
    if (!v.is_active && !selectedIds.value.has(v.id) && v.id !== props.lockedId)
      continue
    const group = byPrompt.get(v.prompt_id) ?? { name: v.prompt?.name || 'Unknown', versions: [] }
    group.versions.push(v)
    byPrompt.set(v.prompt_id, group)
  }

  return [...byPrompt.values()]
    .toSorted((a, b) => a.name.localeCompare(b.name))
    .map(group => [
      { type: 'label' as const, label: group.name },
      ...group.versions.toSorted(byVersionDesc).map((v) => {
        const state = props.itemState?.(v)
        const locked = v.id === props.lockedId
        return {
          label: `${group.name} ${v.version}`,
          value: v.id,
          version: v.version,
          createdAt: v.created_at,
          isDefault: v.is_default,
          inactive: !v.is_active,
          description: locked ? 'Current setup' : state?.description,
          disabled: locked || state?.disabled,
        }
      }),
    ])
})

function onUpdate(value: unknown) {
  // Clearing a single select reports undefined; the callers' forms use null for "none"
  model.value = (props.clearable && (value === undefined || value === null) && !props.multiple ? null : value) as typeof model.value
}
</script>

<template>
  <USelectMenu
    :model-value="(model ?? undefined) as any"
    :multiple="multiple"
    :clear="clearable && !multiple"
    value-key="value"
    :items="items"
    :placeholder="placeholder"
    :search-input="{ placeholder: searchPlaceholder }"
    :ui="{ content: 'min-w-64', item: 'ps-6' }"
    @update:model-value="onUpdate"
  >
    <template #leading>
      <UIcon name="i-ph-chat-text-bold" class="size-4 shrink-0 text-dimmed" aria-hidden="true" />
    </template>

    <template #item-label="{ item }">
      <span class="inline-flex items-center gap-1.5">
        <span class="tabular-nums">{{ (item as any).version }}</span>
        <UIcon
          v-if="(item as any).isDefault"
          name="i-ph-star-bold"
          class="size-3.5 shrink-0 text-muted"
          role="img"
          title="Default version"
          aria-label="Default version"
        />
      </span>
    </template>

    <template #item-trailing="{ item }">
      <span v-if="(item as any).inactive" class="text-xs text-warning">Inactive</span>
      <span v-if="(item as any).createdAt" class="text-xs text-muted tabular-nums">
        {{ formatShortDate((item as any).createdAt) }}
      </span>
    </template>
  </USelectMenu>
</template>
