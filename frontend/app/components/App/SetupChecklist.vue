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
// "Get started": the way to a first run, drawn from what the workspace holds. The first step not done is
// the current one; later ones wait greyed out. It leaves once everything is done, or when hidden.
const { steps, doneCount, current, visible, open, dismissed } = useSetupProgress()

// The progress ring: the circle's circumference is 2π·6 ≈ 37.7
const RING = 37.7
const ringOffset = computed(() => RING * (1 - doneCount.value / steps.value.length))
</script>

<template>
  <section
    v-if="visible"
    aria-labelledby="setup-title"
    class="rounded-lg border border-default bg-default text-sm shadow-xs"
  >
    <div class="flex items-center">
      <button
        type="button"
        class="flex h-9 min-w-0 flex-1 items-center gap-2 rounded-lg px-3 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
        :aria-expanded="open"
        aria-controls="setup-steps"
        @click="() => { open = !open }"
      >
        <svg viewBox="0 0 16 16" class="size-4 shrink-0 -rotate-90" aria-hidden="true">
          <circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2" class="text-accented" />
          <circle
            cx="8"
            cy="8"
            r="6"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            class="text-success"
            :stroke-dasharray="RING"
            :stroke-dashoffset="ringOffset"
          />
        </svg>
        <span id="setup-title" class="flex-1 truncate font-medium text-toned">Get started</span>
        <span class="text-xs tabular-nums text-muted">{{ doneCount }}/{{ steps.length }}</span>
      </button>
      <UTooltip text="Hide for good">
        <UButton
          icon="i-ph-x"
          color="neutral"
          variant="ghost"
          size="xs"
          class="mr-1"
          aria-label="Hide the getting-started list"
          @click="() => { dismissed = true }"
        />
      </UTooltip>
    </div>

    <ul v-if="open" id="setup-steps" class="border-t border-default p-1">
      <li v-for="step in steps" :key="step.id">
        <!-- Three shapes, so progress never rests on color alone -->
        <NuxtLink
          :to="step.to"
          :aria-current="step === current ? 'step' : undefined"
          class="flex h-8 items-center gap-2 rounded-md px-2 outline-none hover:bg-elevated focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
          :class="step.done ? 'text-highlighted' : step === current ? 'text-highlighted' : 'text-muted'"
        >
          <UIcon
            :name="step.done ? 'i-ph-check-circle-fill' : step === current ? 'i-ph-circle-dashed-bold' : 'i-ph-circle-bold'"
            class="size-4 shrink-0"
            :class="step.done ? 'text-success' : step === current ? 'text-primary' : 'text-dimmed'"
            aria-hidden="true"
          />
          <span class="truncate" :class="step.done && 'text-toned'">{{ step.label }}</span>
          <span class="sr-only">{{ step.done ? '(done)' : step === current ? '(next)' : '(later)' }}</span>
        </NuxtLink>
      </li>
    </ul>
  </section>
</template>
