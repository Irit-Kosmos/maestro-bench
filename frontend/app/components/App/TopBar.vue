<script setup lang="ts">
const route = useRoute()
const labels = useBreadcrumbLabels()

const labelMap: Record<string, { label: string, icon: string }> = {
  experiments: { label: 'Experiments', icon: 'i-lucide-flask-conical' },
  batches: { label: 'Batches', icon: 'i-lucide-split' },
  analyses: { label: 'Analyses', icon: 'i-lucide-chart-column' },
  datasets: { label: 'Datasets', icon: 'i-lucide-database' },
  agents: { label: 'Agents', icon: 'i-lucide-bot' },
  prompts: { label: 'Prompts', icon: 'i-lucide-message-square-text' },
  models: { label: 'Models', icon: 'i-lucide-cpu' },
  settings: { label: 'Settings', icon: 'i-lucide-settings' },
  new: { label: 'New', icon: 'i-lucide-plus' },
}

const breadcrumbs = computed(() => {
  if (route.path === '/')
    return [{ label: 'Dashboard', icon: 'i-lucide-layout-dashboard' }]

  const paths = route.path.split('/').filter(Boolean)
  const items: { label: string, to?: string, icon?: string }[] = []

  let currentPath = ''
  for (const segment of paths) {
    currentPath += `/${segment}`
    const mapped = labelMap[segment]
    const label = labels.value[currentPath]
      ?? mapped?.label
      ?? (/^\d+$/.test(segment) ? `#${segment}` : segment)
    items.push({ label, to: currentPath, icon: items.length === 0 ? mapped?.icon : undefined })
  }

  // The current page is not a link to itself
  const last = items[items.length - 1]
  if (last)
    last.to = undefined

  return items
})
</script>

<template>
  <UDashboardNavbar :ui="{ root: 'sm:px-4 gap-3', left: 'min-w-0' }">
    <template #left>
      <UBreadcrumb
        :items="breadcrumbs"
        :ui="{ list: 'min-w-0', item: 'min-w-0', link: 'text-sm min-w-0', linkLabel: 'truncate max-w-[40ch]' }"
      />
    </template>

    <template #right>
      <!-- Pages teleport their primary actions here (see BasePageContent) -->
      <div id="page-actions" class="flex items-center gap-2" />
    </template>
  </UDashboardNavbar>
</template>
