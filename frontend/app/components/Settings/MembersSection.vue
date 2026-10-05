<script setup lang="ts">
import type { CreatedInvitation, WorkspaceInvitation, WorkspaceMember, WorkspaceRole } from '~/types'
import { useClipboard } from '@vueuse/core'
import { apiErrorMessage } from '~/composables/useAnalyses'

const { members: api, invitations: invitationsApi } = useWorkspaceAdmin()
const { can } = useCurrentWorkspace()
const { user } = useAuth()
const { workspaces } = useWorkspaces()
const toast = useToast()

const canManage = computed(() => can('owner'))

const ROLE_ITEMS: { label: string, value: WorkspaceRole }[] = [
  { label: 'Owner', value: 'owner' },
  { label: 'Editor', value: 'editor' },
  { label: 'Viewer', value: 'viewer' },
]
const INVITE_ROLE_ITEMS = ROLE_ITEMS.filter(item => item.value !== 'owner')

const { data: members, refresh } = await useAsyncData('workspace-members', () => api.list(), { lazy: true })
const { data: invitations, refresh: refreshInvitations } = await useAsyncData(
  'workspace-invitations',
  async () => canManage.value ? await invitationsApi.list() : [] as WorkspaceInvitation[],
  { lazy: true },
)

function failed(error: unknown, fallback: string) {
  toast.add({ title: apiErrorMessage(error) ?? fallback, color: 'error', icon: 'i-ph:warning-circle-bold' })
}

// --- Members -----------------------------------------------------------------

async function changeRole(member: WorkspaceMember, role: WorkspaceRole) {
  if (role === member.role)
    return
  try {
    await api.setRole(member.user_id, role)
  }
  catch (error) {
    failed(error, 'The role could not be changed')
  }
  await refresh()
}

const memberToRemove = ref<WorkspaceMember | null>(null)
const removing = ref(false)
const isLeaving = computed(() => memberToRemove.value?.user_id === user.value?.id)

async function removeMember() {
  const member = memberToRemove.value
  if (!member)
    return
  removing.value = true
  try {
    await api.remove(member.user_id)
    memberToRemove.value = null
    if (isLeaving.value) {
      // The workspace is no longer yours: go to one that is, or to the list
      workspaces.value = null
      await navigateTo('/w', { external: true })
      return
    }
    await refresh()
  }
  catch (error) {
    failed(error, 'The member could not be removed')
  }
  finally {
    removing.value = false
  }
}

const email = ref('')
const newRole = ref<WorkspaceRole>('editor')
const adding = ref(false)
const addError = ref<string | null>(null)

async function addMember() {
  if (!email.value.trim() || adding.value)
    return
  adding.value = true
  addError.value = null
  try {
    await api.add(email.value.trim(), newRole.value)
    email.value = ''
    await refresh()
  }
  catch (error) {
    addError.value = (apiErrorMessage(error) ?? 'The member could not be added')
  }
  finally {
    adding.value = false
  }
}

// --- Invitations -------------------------------------------------------------

const inviteRole = ref<WorkspaceRole>('editor')
const creating = ref(false)
const created = ref<{ invitation: CreatedInvitation, link: string } | null>(null)
const { copy, copied } = useClipboard({ copiedDuring: 1500 })

async function createInvitation() {
  creating.value = true
  try {
    const invitation = await invitationsApi.create(inviteRole.value)
    created.value = { invitation, link: invitationsApi.link(invitation.token) }
    await refreshInvitations()
  }
  catch (error) {
    failed(error, 'The invitation could not be created')
  }
  finally {
    creating.value = false
  }
}

async function revoke(invitation: WorkspaceInvitation) {
  try {
    await invitationsApi.revoke(invitation.id)
  }
  catch (error) {
    failed(error, 'The invitation could not be revoked')
  }
  await refreshInvitations()
}

const expires = (invitation: WorkspaceInvitation) => parseApiDate(invitation.expires_at).toLocaleDateString()
</script>

<template>
  <BaseSection title="Members">
    <template #meta>
      <span v-if="members?.length" class="text-xs text-muted tabular-nums">{{ members.length }}</span>
    </template>

    <ul class="divide-y divide-default">
      <li v-for="member in members ?? []" :key="member.user_id" class="flex items-center gap-3 min-h-12 px-4 py-2">
        <UAvatar :src="member.avatar_url ?? undefined" :alt="member.display_name" size="xs" />
        <div class="min-w-0 flex-1">
          <p class="truncate text-sm font-medium text-highlighted">
            {{ member.display_name }}
            <span v-if="member.user_id === user?.id" class="ms-1 text-xs font-normal text-muted">you</span>
          </p>
          <p v-if="member.email" class="truncate text-xs text-muted">
            {{ member.email }}
          </p>
        </div>
        <USelect
          v-if="canManage"
          :model-value="member.role"
          :items="ROLE_ITEMS"
          size="xs"
          class="w-28"
          :aria-label="`Role of ${member.display_name}`"
          @update:model-value="(role: WorkspaceRole) => changeRole(member, role)"
        />
        <span v-else class="w-28 text-end text-xs text-toned capitalize">{{ member.role }}</span>
        <UTooltip
          v-if="canManage || member.user_id === user?.id"
          :text="member.user_id === user?.id ? 'Leave the workspace' : 'Remove from the workspace'"
        >
          <UButton
            :icon="member.user_id === user?.id ? 'i-ph-sign-out-bold' : 'i-ph-user-minus-bold'"
            color="neutral"
            variant="ghost"
            size="xs"
            :aria-label="member.user_id === user?.id ? 'Leave the workspace' : `Remove ${member.display_name}`"
            @click="() => { memberToRemove = member }"
          />
        </UTooltip>
      </li>
    </ul>

    <template v-if="canManage">
      <form class="flex flex-wrap items-start gap-2 px-4 py-3 border-t border-default" @submit.prevent="addMember">
        <UFormField class="min-w-48 flex-1" :error="addError ?? undefined">
          <UInput
            v-model="email"
            type="email"
            size="sm"
            class="w-full"
            placeholder="Add someone by email"
            aria-label="Email of the person to add"
            @input="addError = null"
          />
        </UFormField>
        <USelect v-model="newRole" :items="ROLE_ITEMS" size="sm" class="w-28" aria-label="Role" />
        <UButton type="submit" size="sm" color="neutral" variant="soft" :disabled="!email.trim()" :loading="adding">
          Add
        </UButton>
        <p class="basis-full text-xs text-muted text-pretty">
          They must have signed in once. Otherwise, send an invitation link.
        </p>
      </form>

      <div class="flex flex-col gap-3 px-4 py-3 border-t border-default">
        <div class="flex flex-wrap items-center gap-2">
          <h3 class="me-auto text-sm font-medium text-highlighted">
            Invitation links
          </h3>
          <USelect v-model="inviteRole" :items="INVITE_ROLE_ITEMS" size="sm" class="w-28" aria-label="Role given by the link" />
          <UButton size="sm" color="neutral" variant="soft" icon="i-ph-link-bold" :loading="creating" @click="createInvitation">
            New link
          </UButton>
        </div>

        <div v-if="created" class="flex flex-col gap-1.5 rounded-md border border-default bg-elevated/50 p-3">
          <p class="text-xs text-toned">
            Give this link to the person. It gives the {{ created.invitation.role }} role, works once, and is shown only now.
          </p>
          <div class="flex items-center gap-2">
            <UInput :model-value="created.link" readonly size="sm" class="min-w-0 flex-1 font-mono" aria-label="Invitation link" @focus="($event.target as HTMLInputElement).select()" />
            <UButton size="sm" color="neutral" variant="outline" :icon="copied ? 'i-ph-check-bold' : 'i-ph-copy-bold'" @click="copy(created.link)">
              {{ copied ? 'Copied' : 'Copy' }}
            </UButton>
          </div>
        </div>

        <ul v-if="invitations?.length" class="divide-y divide-default rounded-md border border-default">
          <li v-for="invitation in invitations" :key="invitation.id" class="flex items-center gap-3 h-9 px-3 text-xs">
            <span class="capitalize text-toned">{{ invitation.role }}</span>
            <span class="text-muted">expires {{ expires(invitation) }}</span>
            <UButton class="ms-auto" size="xs" color="neutral" variant="ghost" @click="revoke(invitation)">
              Revoke
            </UButton>
          </li>
        </ul>
        <p v-else-if="!created" class="text-xs text-muted">
          No pending link.
        </p>
      </div>
    </template>

    <BaseConfirmDialog
      :open="!!memberToRemove"
      :title="isLeaving ? 'Leave this workspace' : 'Remove member'"
      :message="isLeaving
        ? 'You will lose access to everything in this workspace until someone adds you back.'
        : `${memberToRemove?.display_name} will lose access to this workspace.`"
      :confirm-label="isLeaving ? 'Leave' : 'Remove'"
      variant="error"
      :loading="removing"
      @update:open="(value: boolean) => { if (!value) memberToRemove = null }"
      @confirm="removeMember"
    />
  </BaseSection>
</template>
