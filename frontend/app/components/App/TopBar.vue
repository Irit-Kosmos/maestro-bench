<script setup lang="ts">
const route = useRoute()
const labels = useBreadcrumbLabels()

const labelMap: Record<string, { label: string, icon: string }> = {
  experiments: { label: 'Experiments', icon: 'i-ph-flask' },
  executions: { label: 'Executions', icon: 'i-ph-clock-counter-clockwise' },
  batches: { label: 'Batches', icon: 'i-ph-arrows-split' },
  analyses: { label: 'Analyses', icon: 'i-ph-chart-bar' },
  datasets: { label: 'Datasets', icon: 'i-ph-database' },
  agents: { label: 'Agents', icon: 'i-ph-robot' },
  prompts: { label: 'Prompts', icon: 'i-ph-chat-text' },
  models: { label: 'Models', icon: 'i-ph-cpu' },
  settings: { label: 'Settings', icon: 'i-ph-gear' },
  new: { label: 'New', icon: 'i-ph-plus' },
}

const breadcrumbs = computed(() => {
  if (route.path === '/')
    return [{ label: 'Dashboard', icon: 'i-ph-squares-four' }]

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
