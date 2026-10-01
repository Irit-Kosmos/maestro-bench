<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const shortcutsOpen = useShortcutsOverlay()

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
  // Create from anywhere: an analysis on analysis pages, an experiment otherwise
  'c': () => {
    router.push(route.path.startsWith('/analyses') ? '/analyses/new' : '/experiments/new')
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
        <slot />
      </template>
    </UDashboardPanel>

    <!-- Command Palette (UDashboardSearch handles meta_k shortcut) -->
    <AppCommandPalette />

    <!-- Shortcuts Overlay -->
    <AppShortcutsOverlay v-model:open="shortcutsOpen" />
  </UDashboardGroup>
</template>
