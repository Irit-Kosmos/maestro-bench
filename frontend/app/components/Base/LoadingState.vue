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
interface Props {
  message?: string
  size?: 'sm' | 'md' | 'lg'
}

withDefaults(defineProps<Props>(), {
  message: 'Loading…',
  size: 'md',
})

const sizeClasses = {
  sm: 'size-4',
  md: 'size-5',
  lg: 'size-6',
}
</script>

<template>
  <div class="flex justify-center items-center gap-2 py-16" role="status">
    <UIcon
      name="i-ph-circle-notch-bold"
      class="animate-spin text-muted motion-reduce:animate-none"
      :class="sizeClasses[size]"
      aria-hidden="true"
    />
    <p class="text-sm text-muted">
      {{ message }}
    </p>
  </div>
</template>
