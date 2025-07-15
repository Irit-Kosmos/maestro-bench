<script setup lang="ts">
// Layout-level composables
const route = useRoute()

// Computed page title for better SEO
const pageTitle = computed(() => {
  // Get title from page meta or fallback to route name
  return (route.meta.title as string) || 'MAESTRO Bench'
})

// Set dynamic head title
useHead({
  title: pageTitle,
})
</script>

<template>
  <div class="min-h-screen bg-neutral-50">
    <!-- Navigation Header -->
    <header class="bg-white border-b border-neutral-200">
      <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex justify-between items-center py-4">
          <!-- Logo -->
          <div class="flex items-center">
            <NuxtLink to="/" class="text-2xl font-bold inline-flex items-center text-neutral-900">
              <img
                src="/MAESTRO-bench.png"
                alt="MAESTRO Bench Logo"
                width="32"
                height="32"
                class="inline-block mr-2"
              >
              <span class="hidden lg:inline">MAESTRO-bench</span>
              <span class="inline lg:hidden">mb</span>
            </NuxtLink>
          </div>

          <!-- Navigation Links -->
          <div class="flex items-center gap-1">
            <UButton
              to="/"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:home"
              :class="{ 'bg-primary-50 text-primary-600': route.path === '/' }"
            >
              <span class="hidden lg:inline">Dashboard</span>
            </UButton>
            <UButton
              to="/experiments"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:flask-conical"
              :class="{ 'bg-primary-50 text-primary-600': route.path.startsWith('/experiments') }"
            >
              <span class="hidden lg:inline">Experiments</span>
            </UButton>
            <UButton
              to="/datasets"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:database"
              :class="{ 'bg-primary-50 text-primary-600': route.path.startsWith('/datasets') }"
            >
              <span class="hidden lg:inline">Datasets</span>
            </UButton>
            <UButton
              to="/agents"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:users"
              :class="{ 'bg-primary-50 text-primary-600': route.path.startsWith('/agents') }"
            >
              <span class="hidden lg:inline">Agents</span>
            </UButton>
            <UButton
              to="/prompts"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:message-square-text"
              :class="{ 'bg-primary-50 text-primary-600': route.path.startsWith('/prompts') }"
            >
              <span class="hidden lg:inline">Prompts</span>
            </UButton>
            <UButton
              to="/models"
              variant="ghost"
              color="neutral"
              size="sm"
              icon="i-lucide:cpu"
              :class="{ 'bg-primary-50 text-primary-600': route.path.startsWith('/models') }"
            >
              <span class="hidden lg:inline">Models</span>
            </UButton>
          </div>
        </div>
      </nav>
    </header>

    <!-- Main Content Area -->
    <main class="min-h-[calc(100vh-80px)]">
      <slot />
    </main>
  </div>
</template>
