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
import type { AuthProvider } from '~/types'

definePageMeta({
  // No sidebar: nobody is signed in yet
  layout: false,
  title: 'Sign in',
})

useSeoMeta({
  title: 'Sign in',
})

const route = useRoute()
const { loginUrl } = useAuth()
const { data: providers, pending, error } = await useMyLazyFetch<AuthProvider[]>('/auth/providers')

const message = computed(() => loginErrorMessage(route.query.error))
const next = computed(() => safeNextPath(route.query.next))
</script>

<template>
  <main class="min-h-dvh flex items-center justify-center p-4 bg-default">
    <div class="w-full max-w-sm flex flex-col gap-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <AppLogo class="size-9 text-highlighted" />
        <div class="flex flex-col gap-1">
          <h1 class="text-lg font-semibold text-highlighted">
            Sign in to MAESTRO-bench
          </h1>
          <p class="text-sm text-muted">
            Use your institutional account.
          </p>
        </div>
      </div>

      <UAlert
        v-if="message"
        color="error"
        variant="subtle"
        icon="i-ph-warning-circle-bold"
        :description="message"
      />

      <div v-if="pending && !providers" class="flex flex-col gap-2">
        <USkeleton class="h-9" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="subtle"
        icon="i-ph-plugs-bold"
        title="Can’t reach the server"
        description="Check that the backend is running, then reload the page."
      />

      <div v-else-if="providers?.length" class="flex flex-col gap-2">
        <UButton
          v-for="provider in providers"
          :key="provider.name"
          :href="loginUrl(provider.name, next)"
          :icon="provider.name === 'gitlab' ? 'i-ph-gitlab-logo' : undefined"
          color="neutral"
          size="lg"
          block
        >
          Continue with {{ provider.label }}
        </UButton>
      </div>

      <UAlert
        v-else
        color="warning"
        variant="subtle"
        icon="i-ph-warning-bold"
        description="No sign-in method is configured. Ask an administrator to enable one."
      />
    </div>
  </main>
</template>
