<script setup lang="ts">
definePageMeta({
  // No sidebar: you may not be in any workspace yet
  layout: false,
  title: 'Workspaces',
})

useSeoMeta({
  title: 'Workspaces',
})

const route = useRoute()
const { workspaces, open, create } = useWorkspaces()
const { user, canCreateWorkspace, logout } = useAuth()
const toast = useStandardToast()

const name = ref('')
const creating = ref(false)

const roleLabels: Record<string, string> = { owner: 'Owner', editor: 'Editor', viewer: 'Viewer' }

async function submit() {
  if (!name.value.trim() || creating.value)
    return
  creating.value = true
  try {
    const created = await create(name.value)
    await open(created.slug)
  }
  catch (error: any) {
    toast.showCreateError('workspace', error?.data?.detail)
    creating.value = false
  }
}
</script>

<template>
  <main class="min-h-dvh flex items-center justify-center p-4 bg-default">
    <div class="w-full max-w-md flex flex-col gap-6">
      <div class="flex flex-col items-center gap-3 text-center">
        <img src="/MAESTRO-bench.png" alt="" class="h-10 w-auto">
        <div class="flex flex-col gap-1">
          <h1 class="text-lg font-semibold text-highlighted">
            {{ workspaces?.length ? 'Your workspaces' : 'No workspace yet' }}
          </h1>
          <p class="text-sm text-muted">
            <template v-if="workspaces?.length">
              Pick the one to work in.
            </template>
            <template v-else-if="canCreateWorkspace">
              Create one to get started, or ask an owner to add you to theirs.
            </template>
            <template v-else>
              Ask a workspace owner to add you{{ user?.email ? ` (${user.email})` : '' }}.
            </template>
          </p>
        </div>
      </div>

      <ul v-if="workspaces?.length" class="flex flex-col divide-y divide-default rounded-lg border border-default overflow-hidden">
        <li v-for="workspace in workspaces" :key="workspace.slug">
          <button
            type="button"
            class="flex w-full items-center gap-3 h-11 px-4 text-start outline-none hover:bg-elevated focus-visible:bg-elevated focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted"
            @click="open(workspace.slug)"
          >
            <span class="min-w-0 flex-1 truncate text-sm font-medium text-highlighted">{{ workspace.name }}</span>
            <UBadge v-if="workspace.archived" color="neutral" variant="subtle" size="sm">
              Archived
            </UBadge>
            <span class="shrink-0 text-xs text-muted">{{ roleLabels[workspace.role] }}</span>
          </button>
        </li>
      </ul>

      <form v-if="canCreateWorkspace" class="flex gap-2" @submit.prevent="submit">
        <UInput
          v-model="name"
          placeholder="New workspace name"
          aria-label="New workspace name"
          :autofocus="'new' in route.query"
          maxlength="80"
          class="flex-1"
        />
        <UButton type="submit" color="neutral" :loading="creating" :disabled="!name.trim()">
          Create
        </UButton>
      </form>

      <div class="flex justify-center">
        <UButton color="neutral" variant="link" size="sm" @click="logout">
          Sign out
        </UButton>
      </div>
    </div>
  </main>
</template>
