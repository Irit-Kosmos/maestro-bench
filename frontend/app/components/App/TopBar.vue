<script setup lang="ts">
const route = useRoute()

const breadcrumbs = computed(() => {
  const paths = route.path.split('/').filter(Boolean)
  const items: { label: string, to?: string, icon?: string }[] = []

  const labelMap: Record<string, { label: string, icon: string }> = {
    experiments: { label: 'Experiments', icon: 'i-lucide-flask-conical' },
    datasets: { label: 'Datasets', icon: 'i-lucide-database' },
    agents: { label: 'Agents', icon: 'i-lucide-bot' },
    prompts: { label: 'Prompts', icon: 'i-lucide-message-square-text' },
    models: { label: 'Models', icon: 'i-lucide-cpu' },
    new: { label: 'New', icon: 'i-lucide-plus' },
  }

  let currentPath = ''
  for (const segment of paths) {
    currentPath += `/${segment}`
    const mapped = labelMap[segment]
    if (mapped) {
      items.push({ label: mapped.label, to: currentPath, icon: items.length === 0 ? mapped.icon : undefined })
    }
    else if (/^\d+$/.test(segment)) {
      items.push({ label: `#${segment}`, to: currentPath })
    }
    else {
      items.push({ label: segment, to: currentPath })
    }
  }

  return items
})

const pageTitle = computed(() => {
  if (route.path === '/') return 'Dashboard'
  const last = breadcrumbs.value[breadcrumbs.value.length - 1]
  return last?.label || ''
})

const subtitle = computed(() => (route.meta.subtitle as string) || '')
</script>

<template>
  <UDashboardNavbar :title="breadcrumbs.length <= 1 && !subtitle ? pageTitle : undefined">
    <template v-if="breadcrumbs.length > 1" #left>
      <UBreadcrumb :items="breadcrumbs" />
    </template>

    <template v-else-if="subtitle" #left>
      <div>
        <h1 class="text-lg font-semibold">
          {{ pageTitle }}
        </h1>
        <p class="text-sm text-neutral-500">
          {{ subtitle }}
        </p>
      </div>
    </template>

  </UDashboardNavbar>
</template>
