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
// Name and description, edited in place at the top of the page like a document title: no section of their own
interface Props {
  experimentDetails: {
    name: string
    description: string
  }
  /** Naming a batch: its experiments get this name plus what varies */
  batch?: boolean
}

interface Emits {
  'update:name': [value: string]
  'update:description': [value: string]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// Two-way binding computed properties
const name = computed({
  get: () => props.experimentDetails.name,
  set: (value: string) => emit('update:name', value),
})

const description = computed({
  get: () => props.experimentDetails.description,
  set: (value: string) => emit('update:description', value),
})

const hintId = useId()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <UInput
      id="experiment-name"
      v-model="name"
      variant="none"
      size="xl"
      :placeholder="batch ? 'Batch name' : 'Experiment name'"
      :aria-label="batch ? 'Batch name' : 'Name'"
      aria-required="true"
      :aria-describedby="batch ? hintId : undefined"
      autofocus
      class="w-full"
      :ui="{ base: 'px-0 py-0 text-2xl/9 font-semibold tracking-tight text-highlighted placeholder:text-dimmed sm:text-3xl/10' }"
    />
    <p v-if="batch" :id="hintId" class="text-xs text-muted">
      Each experiment is named after it, plus what varies.
    </p>

    <UTextarea
      v-model="description"
      variant="none"
      placeholder="Add a description: what are you testing?"
      aria-label="Description"
      :rows="1"
      autoresize
      class="w-full"
      :ui="{ base: 'px-0 py-0.5 text-sm text-toned placeholder:text-dimmed resize-none' }"
    />
  </div>
</template>
