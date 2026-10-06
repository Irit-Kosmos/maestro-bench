<script setup lang="ts">
const route = useRoute()
const { relativePath } = useWorkspace()
const router = useRouter()
const shortcutsOpen = useShortcutsOverlay()
const { toggle: toggleTheme } = useTheme()
const { archived, canEdit } = useCurrentWorkspace()

const pageTitle = computed(() => {
  return (route.meta.title as string) || 'MAESTRO-bench'
})

useHead({
  title: pageTitle,
})

// Global keyboard shortcuts
defineShortcuts({
  '?': () => {
    shortcutsOpen.value = true
  },
  'g-h': () => {
    router.push('/')
  },
  'g-e': () => {
    router.push('/experiments')
  },
  'g-x': () => {
    router.push('/executions')
  },
  'g-b': () => {
    router.push('/batches')
  },
  'g-n': () => {
    router.push('/analyses')
  },
  'g-d': () => {
    router.push('/datasets')
  },
  'g-a': () => {
    router.push('/agents')
  },
  'g-p': () => {
    router.push('/prompts')
  },
  'g-m': () => {
    router.push('/models')
  },
  'g-s': () => {
    router.push('/settings')
  },
  // Instant on purpose: a keyboard action should never wait on an animation
  't': toggleTheme,
  // Create from anywhere: what the page lists, or an experiment on the pages that list nothing creatable
  'c': () => {
    if (!canEdit.value)
      return
    const path = relativePath.value
    if (path.startsWith('/analyses'))
      return router.push('/analyses/new')
    const listed = ['/datasets', '/prompts', '/agents', '/models'].find(prefix => path.startsWith(prefix))
    router.push(listed ? `${listed}?new=1` : '/experiments/new')
  },
})
</script>

<template>
  <!-- px + local storage: the sidebar keeps the width you dragged it to -->
  <UDashboardGroup unit="px" storage="local" storage-key="maestro">
    <AppSidebar />

    <UDashboardPanel id="main" :ui="{ body: 'p-4 sm:px-8 sm:py-6' }">
      <template #header>
        <AppTopBar />
      </template>

      <template #body>
        <UAlert
          v-if="archived"
          class="mb-4 shrink-0"
          color="warning"
          variant="subtle"
          icon="i-ph-archive-bold"
          title="This workspace is archived"
          description="It is read-only. An owner can reopen it in Settings."
        />
        <slot />
      </template>
    </UDashboardPanel>

    <!-- Command Palette (UDashboardSearch handles meta_k shortcut) -->
    <AppCommandPalette />

    <!-- Shortcuts Overlay -->
    <AppShortcutsOverlay v-model:open="shortcutsOpen" />
  </UDashboardGroup>
</template>
