<script setup lang="ts">
const route = useRoute()
const { relativePath } = useWorkspace()
const router = useRouter()
const shortcutsOpen = useShortcutsOverlay()
const { toggle: toggleTheme } = useTheme()
const { archived, canEdit } = useCurrentWorkspace()

usePrintLight()

// The skip link focuses <main> by hand: the router would swallow a plain #hash jump without moving focus
const main = useTemplateRef<HTMLElement>('main')

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
  'g-y': () => {
    router.push('/studies')
  },
  'g-s': () => {
    router.push('/settings')
  },
  // Linear's "open workspaces"
  'o-w': () => {
    router.push('/w')
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
    const listed = ['/datasets', '/prompts', '/agents', '/models', '/studies'].find(prefix => path.startsWith(prefix))
    router.push(listed ? `${listed}?new=1` : '/experiments/new')
  },
})
</script>

<template>
  <!-- px + local storage: the sidebar keeps the width you dragged it to -->
  <!-- print: the shell is a fixed, clipped viewport; on paper it flows, so long pages span several sheets -->
  <UDashboardGroup
    unit="px"
    storage="local"
    storage-key="maestro"
    :ui="{ base: 'print:static print:block print:overflow-visible' }"
  >
    <!-- First thing a keyboard user reaches; off screen until focused -->
    <a
      href="#main-content"
      class="fixed start-3 top-3 z-100 -translate-y-[200%] rounded-md bg-default px-3 py-1.5 text-sm font-medium text-highlighted shadow-sm ring ring-default outline-none focus:translate-y-0 focus-visible:ring-2 focus-visible:ring-inverted print:hidden"
      @click.prevent="main?.focus()"
    >
      Skip to content
    </a>

    <AppSidebar />

    <UDashboardPanel
      id="main"
      :ui="{
        root: 'print:min-h-0 print:block',
        // The body wrapper steps aside: <main> below takes its place (and its classes) so the content has a landmark
        body: 'contents',
      }"
    >
      <template #header>
        <AppTopBar />
      </template>

      <template #body>
        <main
          id="main-content"
          ref="main"
          tabindex="-1"
          class="flex flex-1 flex-col gap-4 overflow-y-auto p-4 outline-none [scrollbar-gutter:stable] sm:gap-6 sm:px-8 sm:py-6 print:block print:overflow-visible print:p-1"
        >
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
        </main>
      </template>
    </UDashboardPanel>

    <!-- Command Palette (UDashboardSearch handles meta_k shortcut) -->
    <AppCommandPalette />

    <!-- Shortcuts Overlay -->
    <AppShortcutsOverlay v-model:open="shortcutsOpen" />
  </UDashboardGroup>
</template>
