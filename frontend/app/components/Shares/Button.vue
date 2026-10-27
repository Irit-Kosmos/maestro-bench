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
import type { ShareKind } from '~/types'

// The Share button of an item's page, with the dialog it opens. An editor of an archived workspace can still open
// it, to see the link and to stop sharing; making links is left out there.
defineProps<{
  kind: ShareKind
  itemId: number
}>()

const { publicSharing } = useAuth()
const { isShared } = useShare()
const { role, archived } = useCurrentWorkspace()

const open = ref(false)
const allowed = computed(() => role.value === 'editor' || role.value === 'owner')
</script>

<template>
  <template v-if="publicSharing && !isShared">
    <UIGuardedButton
      archived-ok
      :data-tooltip="allowed ? 'Give a read-only link to anyone, without an account' : undefined"
      color="neutral"
      variant="soft"
      icon="i-ph-share-network-bold"
      size="sm"
      @click="() => { open = true }"
    >
      Share
    </UIGuardedButton>
    <SharesDialog v-if="allowed" v-model:open="open" :kind="kind" :item-id="itemId" :archived="archived" />
  </template>
</template>
