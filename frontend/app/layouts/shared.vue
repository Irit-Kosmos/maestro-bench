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
      <a href="/" class="flex items-center gap-2 text-sm font-semibold text-highlighted outline-none focus-visible:ring-2 focus-visible:ring-inverted">
        <AppLogo class="size-4" />
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
