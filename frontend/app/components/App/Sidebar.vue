<script setup lang="ts">
const route = useRoute()

const configChildren = [
  {
    label: 'Agents',
    icon: 'i-lucide-bot',
    to: '/agents',
  },
  {
    label: 'Prompts',
    icon: 'i-lucide-message-square-text',
    to: '/prompts',
  },
  {
    label: 'Models',
    icon: 'i-lucide-cpu',
    to: '/models',
  },
]

const baseItems = computed(() => [
  {
    label: 'Dashboard',
    icon: 'i-lucide-layout-dashboard',
    to: '/',
    active: route.path === '/',
  },
  {
    label: 'Experiments',
    icon: 'i-lucide-flask-conical',
    to: '/experiments',
    active: route.path.startsWith('/experiments'),
  },
  {
    label: 'Datasets',
    icon: 'i-lucide-database',
    to: '/datasets',
    active: route.path.startsWith('/datasets'),
  },
])

const items = computed(() => [
  [
    ...baseItems.value,
    {
      label: 'Configurations',
      icon: 'i-lucide-settings',
      defaultOpen: true,
      children: configChildren,
    },
  ],
])
</script>

<template>
  <UDashboardSidebar collapsible>
    <template #header="{ collapsed }">
      <div class="flex items-center justify-between gap-2 min-w-0 w-full">
        <NuxtLink
          v-if="!collapsed"
          to="/" class="flex items-center gap-2 min-w-0"
        >
          <img
            src="/MAESTRO-bench.png"
            alt="MAESTRO-bench"
            width="28"
            height="28"
            class="shrink-0"
          >
          <span class="text-sm pt-1 font-semibold text-neutral-700 truncate">MAESTRO-bench</span>
        </NuxtLink>
      </div>
    </template>

    <template #default>
      <UNavigationMenu
        :items="items"
        orientation="vertical"
        highlight
        color="primary"
        variant="pill"
        class="w-full"
      />
    </template>

    <template #footer="{ collapsed }">
      <div class="flex flex-col gap-1 w-full">
        <UDashboardSearchButton :collapsed="collapsed" label="" block />
      </div>
    </template>
  </UDashboardSidebar>
</template>
