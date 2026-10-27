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
// The models an experiment or a run mobilises: one reads as a model (logo and name); several as
// their providers' logos overlapped, then the first model and how many more. The title lists them all.
const props = defineProps<{
  models: readonly { name: string, provider: string }[]
}>()

const distinct = computed(() => {
  const seen = new Map(props.models.map(model => [`${model.provider}/${model.name}`, model]))
  return [...seen.values()]
})

// One logo per provider, at most three: ten models from two providers are still two logos
const providers = computed(() => [...new Set(distinct.value.map(model => providerMeta(model.provider).key))].slice(0, 3))

const title = computed(() => distinct.value.map(model => `${model.name} · ${providerLabel(model.provider)}`).join('\n'))
</script>

<template>
  <span v-if="!distinct.length" class="text-dimmed">—</span>
  <ModelsLabel v-else-if="distinct.length === 1" :name="distinct[0]!.name" :provider="distinct[0]!.provider" />
  <span v-else class="inline-flex min-w-0 max-w-full items-center gap-1.5 align-middle" :title="title">
    <span class="flex shrink-0 items-center -space-x-1.5">
      <UIProviderIcon v-for="key in providers" :key="key" :provider="key" class="size-3.5" />
    </span>
    <span class="truncate">{{ distinct[0]!.name }}</span>
    <span class="shrink-0 text-muted tabular-nums">+{{ distinct.length - 1 }}</span>
    <!-- The title only reaches the pointer: the other models are also text -->
    <span class="sr-only">({{ distinct.slice(1).map(model => model.name).join(', ') }})</span>
  </span>
</template>
