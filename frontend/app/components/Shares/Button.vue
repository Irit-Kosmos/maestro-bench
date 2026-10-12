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
