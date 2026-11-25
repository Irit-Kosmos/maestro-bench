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
// The temperatures a variation runs: the current one, locked, then the ones added.
// A value is added with Enter, the Add button or by leaving the field, so nothing typed is lost.
const props = defineProps<{
  /** Temperature of the current setup, null when the step leaves it to the model */
  base: number | null
  /** The model's own default, shown when the current setup leaves the temperature empty */
  modelDefault?: number | null
}>()

const extras = defineModel<number[]>({ required: true })

const MAX = 2
const draft = ref('')

function parse(raw: string): number | null {
  const text = raw.trim().replace(',', '.')
  if (text === '')
    return null
  const value = Number(text)
  return Number.isFinite(value) && value >= 0 && value <= MAX ? Math.round(value * 100) / 100 : null
}

const parsed = computed(() => parse(draft.value))
const duplicate = computed(() => parsed.value !== null && (parsed.value === props.base || extras.value.includes(parsed.value)))
const error = computed(() => {
  if (draft.value.trim() === '')
    return null
  if (parsed.value === null)
    return `A number between 0 and ${MAX}`
  return duplicate.value ? 'Already in the list' : null
})

function commit() {
  if (parsed.value === null || duplicate.value)
    return
  extras.value = [...extras.value, parsed.value].sort((a, b) => a - b)
  draft.value = ''
}

// Leaving the field keeps a valid value instead of dropping it
function onBlur() {
  if (error.value === null)
    commit()
}

function remove(value: number) {
  extras.value = extras.value.filter(v => v !== value)
}

const baseLabel = computed(() => {
  if (props.base !== null)
    return String(props.base)
  return props.modelDefault != null ? `Default (${props.modelDefault})` : 'Model default'
})
</script>

<template>
  <div class="flex min-w-0 flex-col gap-1">
    <div class="flex min-w-0 flex-wrap items-center gap-1.5">
      <UTooltip text="Current setup: always run">
        <span class="inline-flex h-7 items-center gap-1 rounded-md bg-elevated px-2 text-sm tabular-nums text-toned">
          <UIcon name="i-ph-lock-simple-bold" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
          {{ baseLabel }}
        </span>
      </UTooltip>

      <span
        v-for="value in extras"
        :key="value"
        class="inline-flex h-7 items-center gap-0.5 rounded-md border border-default pl-2 pr-0.5 text-sm tabular-nums"
      >
        {{ value }}
        <UButton
          icon="i-ph-x-bold"
          color="neutral"
          variant="link"
          size="xs"
          :aria-label="`Remove temperature ${value}`"
          @click="remove(value)"
        />
      </span>

      <UInput
        v-model="draft"
        inputmode="decimal"
        size="sm"
        placeholder="e.g. 0.5"
        class="w-24"
        :color="error ? 'error' : undefined"
        :highlight="!!error"
        aria-label="Temperature to add"
        @keydown.enter.prevent="commit"
        @blur="onBlur"
      />
      <UButton
        icon="i-ph-plus-bold"
        color="neutral"
        variant="outline"
        size="sm"
        :disabled="parsed === null || duplicate"
        @mousedown.prevent
        @click="commit"
      >
        Add
      </UButton>
    </div>
    <p v-if="error" class="text-xs text-error">
      {{ error }}
    </p>
  </div>
</template>
