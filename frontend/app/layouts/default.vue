<script setup lang="ts">
const route = useRoute()
const router = useRouter()
const shortcutsOpen = ref(false)

const pageTitle = computed(() => {
  return (route.meta.title as string) || 'MAESTRO Bench'
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
  c: () => {
    if (route.path.startsWith('/experiments')) {
      router.push('/experiments/new')
    }
  },
})
</script>

<template>
  <UDashboardGroup>
    <AppSidebar />

    <UDashboardPanel id="main">
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
