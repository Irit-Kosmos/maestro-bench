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
// The columns of a dataset added to a batch, matched with the base dataset's: the agents read its
// rows under the base names. A column of the same name (whatever its case) matches by default.
const props = defineProps<{
  name: string
  baseHeaders: readonly string[]
  /** Columns of this dataset; undefined while they load */
  headers?: readonly string[]
  /** Base columns the pipeline reads: each one needs a column here */
  used: readonly string[]
  failed?: boolean
}>()

const picks = defineModel<Record<string, string>>('picks', { default: () => ({}) })

// Select items cannot have an empty value: this one stands for "no column"
const NONE = '__none__'

const missing = computed(() => props.headers ? missingColumns(props.used, props.headers, picks.value) : [])
const shadowed = computed(() => props.headers ? shadowedColumns(columnMap(props.baseHeaders, props.headers, picks.value), props.headers) : [])
const renamed = computed(() => props.headers
  ? Object.entries(columnMap(props.baseHeaders, props.headers, picks.value)).filter(([base, column]) => base !== column).length
  : 0)

// Required columns first: they are the ones to complete
const rows = computed(() => {
  const used = new Set(props.used)
  return [...props.baseHeaders]
    .sort((a, b) => Number(used.has(b)) - Number(used.has(a)))
    .map(base => ({ base, required: used.has(base) }))
})

const items = computed(() => [
  { label: 'No column', value: NONE },
  ...(props.headers ?? []).map(header => ({ label: header, value: header })),
])

// Opens by itself when something needs a choice; the person can close it again
const open = ref(false)
watch(() => missing.value.length > 0, (needed) => {
  if (needed)
    open.value = true
}, { immediate: true })

function valueOf(base: string) {
  return columnFor(base, props.headers ?? [], picks.value) ?? NONE
}

function pick(base: string, value: string) {
  picks.value = { ...picks.value, [base]: value === NONE ? '' : value }
}
</script>

<template>
  <UCollapsible v-model:open="open" class="group/columns rounded-md border border-default">
    <!-- Native button: a full-width row shouldn't inherit the press scale of UButton -->
    <button
      type="button"
      class="flex h-9 w-full items-center gap-2 px-3 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
    >
      <UIcon
        name="i-ph-caret-right-bold"
        class="size-3.5 shrink-0 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none group-data-[state=open]/columns:rotate-90"
        aria-hidden="true"
      />
      <UIcon name="i-ph-database-bold" class="size-4 shrink-0 text-muted" aria-hidden="true" />
      <span class="min-w-0 flex-1 truncate text-sm text-highlighted">{{ name }} · columns</span>
      <span v-if="failed" class="shrink-0 text-xs text-error">Couldn’t read its columns</span>
      <span v-else-if="!headers" class="shrink-0 text-xs text-muted">Loading…</span>
      <UBadge
        v-else-if="missing.length > 0"
        color="warning"
        variant="subtle"
        size="sm"
        :label="`${missing.length} to complete`"
      />
      <span v-else class="flex shrink-0 items-center gap-1 text-xs text-muted">
        <UIcon name="i-ph-check-bold" class="size-3.5 text-success" aria-hidden="true" />
        {{ renamed > 0 ? `${renamed} renamed` : 'All columns match' }}
      </span>
    </button>

    <template #content>
      <div v-if="headers" class="border-t border-default px-3 py-2.5">
        <p class="mb-2 text-xs text-muted text-pretty">
          The agents read this dataset’s rows under the names of the base dataset. Choose the column that stands for each one.
        </p>
        <ul class="grid gap-1.5">
          <li
            v-for="row in rows"
            :key="row.base"
            class="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-2"
          >
            <span class="flex min-w-0 items-center gap-1.5">
              <span class="truncate font-mono text-xs text-toned">{{ row.base }}</span>
              <span v-if="row.required" class="shrink-0 text-xs text-muted">used</span>
            </span>
            <UIcon name="i-ph-arrow-left-bold" class="size-3.5 text-dimmed" aria-hidden="true" />
            <USelect
              :model-value="valueOf(row.base)"
              :items="items"
              size="sm"
              class="w-full font-mono"
              :color="row.required && valueOf(row.base) === NONE ? 'warning' : undefined"
              :highlight="row.required && valueOf(row.base) === NONE"
              :aria-label="`Column of ${name} for ${row.base}`"
              @update:model-value="(value) => pick(row.base, value as string)"
            />
          </li>
        </ul>
        <p v-for="base in shadowed" :key="base" class="mt-2 flex items-start gap-1.5 text-xs text-warning">
          <UIcon name="i-ph-warning-bold" class="mt-px size-3.5 shrink-0" aria-hidden="true" />
          Its own “{{ base }}” column gives way to the one chosen above.
        </p>
      </div>
    </template>
  </UCollapsible>
</template>
