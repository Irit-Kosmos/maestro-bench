<script setup lang="ts">
import { apiErrorMessage } from '~/composables/useAnalyses'

definePageMeta({
  // No sidebar: the visitor is not in the workspace yet
  layout: false,
  title: 'Join a workspace',
})

useSeoMeta({
  title: 'Join a workspace',
})

const token = String(useRoute().params.token)
const invitation = useInvitation(token)
const { open, workspaces } = useWorkspaces()

const { data: offer, error, pending } = await useAsyncData(`invitation-${token}`, () => invitation.preview(), { lazy: true })

const joining = ref(false)
const joinError = ref<string | null>(null)

async function join() {
  joining.value = true
  joinError.value = null
  try {
    const accepted = await invitation.accept()
    // Reload the list of workspaces with the new one in it
    workspaces.value = null
    await open(accepted.slug)
  }
  catch (e) {
    joinError.value = apiErrorMessage(e) ?? 'The invitation could not be accepted. Try again, or ask for a new link.'
    joining.value = false
  }
}

const roleText: Record<string, string> = {
  viewer: 'read everything',
  editor: 'read, create and run experiments',
  owner: 'manage the workspace',
}
</script>

<template>
  <main class="min-h-dvh flex items-center justify-center p-4 bg-default">
    <div class="w-full max-w-sm flex flex-col gap-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <AppLogo class="size-9 text-highlighted" />
        <h1 class="text-lg font-semibold text-highlighted">
          Join a workspace
        </h1>
      </div>

      <div v-if="pending && !offer" class="flex flex-col gap-2">
        <USkeleton class="h-4" />
        <USkeleton class="h-9" />
      </div>

      <UAlert
        v-else-if="error"
        color="error"
        variant="subtle"
        icon="i-ph-link-break-bold"
        title="This link doesn’t work"
        description="It may have been used, revoked or expired. Ask for a new one."
      />

      <template v-else-if="offer">
        <p class="text-sm text-toned text-center text-pretty">
          <template v-if="offer.invited_by">
            <span class="font-medium text-highlighted">{{ offer.invited_by }}</span> invites you to join
          </template>
          <template v-else>
            You are invited to join
          </template>
          <span class="font-medium text-highlighted"> {{ offer.workspace_name }}</span>
          as <span class="font-medium text-highlighted">{{ offer.role }}</span>: you can {{ roleText[offer.role] }}.
        </p>

        <UAlert v-if="joinError" color="error" variant="subtle" icon="i-ph-warning-circle-bold" :description="joinError" />

        <UButton block :loading="joining" @click="join">
          Join {{ offer.workspace_name }}
        </UButton>
        <UButton block color="neutral" variant="ghost" to="/w">
          Not now
        </UButton>
      </template>
    </div>
  </main>
</template>
