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
import type { FetchErrorKind } from '~/utils/fetchError'

interface SharedRoot {
  kind: 'experiment' | 'batch' | 'analysis' | 'study'
  item_id: number
  name: string
}

// The page of what the link points to, in the app's own page for it
const PAGES: Record<SharedRoot['kind'], string> = {
  experiment: 'experiments',
  batch: 'batches',
  analysis: 'analyses',
  study: 'studies',
}

const { token } = useShare()
const { $api } = useNuxtApp()

const error = ref<FetchErrorKind | null>(null)

onMounted(async () => {
  try {
    const root = await $api<SharedRoot>('/')
    await navigateTo(inShare(token.value!, `/${PAGES[root.kind]}/${root.item_id}`), { replace: true })
  }
  catch (e) {
    error.value = fetchErrorKind(e)
  }
})
</script>

<template>
  <BaseErrorState
    v-if="error"
    :kind="error"
    :title="error === 'not-found' ? 'This link doesn’t exist' : undefined"
    :message="error === 'not-found' ? 'Check the address, or ask for the link again.' : undefined"
    @retry="reloadNuxtApp()"
  />
  <BaseLoadingState v-else />
</template>
