<script setup lang="ts">
const { toggle: toggleTheme } = useTheme()

usePrintLight()

// The link is in the address: keep the page out of search engines and the address out of what it links to
useHead({
  meta: [
    { name: 'robots', content: 'noindex, nofollow' },
    { name: 'referrer', content: 'no-referrer' },
  ],
})

defineShortcuts({
  t: toggleTheme,
})
</script>

<template>
  <!-- What a public link opens: the page of the app, without the app around it -->
  <div class="flex min-h-dvh flex-col bg-default">
    <a
      href="#main-content"
      class="fixed start-3 top-3 z-100 -translate-y-[200%] rounded-md bg-default px-3 py-1.5 text-sm font-medium text-highlighted shadow-sm ring ring-default outline-none focus:translate-y-0 focus-visible:ring-2 focus-visible:ring-inverted"
    >
      Skip to content
    </a>

    <header class="flex items-center gap-3 border-b border-default px-4 py-2 sm:px-8 print:hidden">
      <!-- A plain link: it leaves the shared page for the app, and must not be taken for one of the link's pages -->
      <a href="/" class="text-sm font-semibold text-highlighted outline-none focus-visible:ring-2 focus-visible:ring-inverted">
        MAESTRO-bench
      </a>
      <UBadge label="Shared, read-only" icon="i-ph-eye-bold" color="neutral" variant="subtle" size="sm" />
      <div class="ms-auto flex items-center gap-2">
        <div id="page-actions" class="flex items-center gap-2" />
        <AppThemeToggle />
      </div>
    </header>

    <main
      id="main-content"
      tabindex="-1"
      class="flex flex-1 flex-col gap-4 p-4 outline-none sm:gap-6 sm:px-8 sm:py-6 print:block print:p-1"
    >
      <slot />
    </main>
  </div>
</template>
