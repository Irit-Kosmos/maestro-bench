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
import type { Placeholder, PlaceholderSegment } from '~/utils/promptPlaceholders'

interface Props {
  label: string
  content: string
  type?: 'text' | 'code'
  /** Declared variable names to pick out in the text, as `{{ name }}` or `<name>`; other `{{ name }}` are flagged */
  variables?: readonly string[]
  /** Variable shown stronger, while it is looked at elsewhere */
  active?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  type: 'code',
  variables: () => [],
  active: null,
})

// The text cut into plain runs and variable placeholders, so the placeholders can be marked up
const segments = computed<PlaceholderSegment[]>(() => props.type === 'code'
  ? splitPlaceholders(props.content, props.variables)
  : [{ text: props.content }])

function markClass(placeholder: Placeholder) {
  if (!placeholder.declared)
    return 'bg-warning/15 text-warning underline decoration-wavy underline-offset-2'
  return placeholder.name === props.active ? 'bg-primary/25 text-primary-700 dark:text-primary' : 'bg-primary/10 text-primary-700 dark:text-primary'
}

function markTitle(placeholder: Placeholder) {
  return placeholder.declared ? undefined : `${placeholder.name} is not declared as a variable`
}
</script>

<template>
  <section>
    <div class="mb-1.5 flex h-6 items-center justify-between">
      <h3 class="text-xs font-medium text-muted">
        {{ label }}
      </h3>
      <UICopyButton v-if="type === 'code'" :text="content" :label="label.toLowerCase()" />
    </div>

    <pre
      v-if="type === 'code'"
      class="whitespace-pre-wrap break-words rounded-md border border-default bg-muted/50 px-3 py-2.5 font-mono text-[13px] leading-relaxed text-highlighted"
    ><template v-for="(segment, index) in segments" :key="index"><mark v-if="segment.placeholder" class="rounded-sm px-0.5 transition-colors duration-100" :class="markClass(segment.placeholder)" :title="markTitle(segment.placeholder)">{{ segment.text }}<span v-if="markTitle(segment.placeholder)" class="sr-only select-none"> ({{ markTitle(segment.placeholder) }})</span></mark><template v-else>{{ segment.text }}</template></template></pre>

    <p v-else class="whitespace-pre-wrap text-sm leading-relaxed text-toned">
      {{ content }}
    </p>
  </section>
</template>
