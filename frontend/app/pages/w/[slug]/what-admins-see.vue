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
import type { AdminField, AdminVisibility } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

definePageMeta({
  title: 'What administrators can see',
})

useSeoMeta({
  title: 'What administrators can see',
  description: 'Exactly what the administrators of this instance can see, and why.',
})

// Generated from the same list the admin API is held to (backend/admin/fields.py): the two cannot drift apart
const { data: visibility, pending, error } = await useMyLazyFetch<AdminVisibility>('/admin/visibility')
const { user } = useAuth()
useBreadcrumbLabel('What administrators can see')

// A small table (the monthly usage) reads as one line: its columns, each explained on hover
function columns(field: AdminField): string {
  return field.fields.filter(f => f.key !== 'month').map(f => f.label).join(' · ')
}
</script>

<template>
  <BasePageContent :loading="pending && !visibility" :error="error ? (apiErrorMessage(error) ?? true) : null">
    <div class="flex flex-col gap-6 max-w-3xl">
      <p class="text-sm text-muted">
        Everything the instance administrators see in the app, and why. Nothing else.
        <template v-if="visibility">
          {{ visibility.administration_only }}
        </template>
        <NuxtLink v-if="user?.is_instance_admin" to="/admin" class="text-highlighted underline underline-offset-2 decoration-dotted hover:decoration-solid">
          Open the administration page
        </NuxtLink>
      </p>

      <BaseSection v-for="section in visibility?.sections ?? []" :key="section.key" :title="section.title">
        <template #meta>
          <span class="hidden truncate text-xs text-muted sm:block" :title="section.task">{{ section.task }}</span>
        </template>
        <dl class="divide-y divide-default">
          <div v-for="field in section.fields" :key="field.key" class="grid grid-cols-1 gap-x-4 px-4 py-2 sm:grid-cols-[11rem_1fr]">
            <dt class="text-sm text-highlighted">
              {{ field.label }}
            </dt>
            <dd class="text-sm text-muted">
              {{ field.purpose }}
              <span
                v-if="field.fields.length"
                class="mt-0.5 block text-xs text-dimmed"
                :title="field.fields.map(f => `${f.label}: ${f.purpose}`).join('\n')"
              >{{ columns(field) }}</span>
            </dd>
          </div>
        </dl>
      </BaseSection>

      <BaseSection v-if="visibility" title="Never shown">
        <ul class="divide-y divide-default">
          <li v-for="item in visibility.never_shown" :key="item" class="flex items-start gap-2 px-4 py-2 text-sm text-muted">
            <UIcon name="i-ph-eye-slash" class="mt-0.5 size-4 shrink-0 text-dimmed" aria-hidden="true" />
            {{ item }}
          </li>
        </ul>
      </BaseSection>

      <p v-if="visibility" class="text-xs text-dimmed">
        Whoever runs the server can still reach the database and files directly: this page covers what the app shows.
      </p>
    </div>
  </BasePageContent>
</template>
