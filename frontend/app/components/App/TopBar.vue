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
const { relativePath } = useWorkspace()
const labels = useBreadcrumbLabels()

const labelMap: Record<string, { label: string, icon: string }> = {
  experiments: { label: 'Experiments', icon: 'i-ph-flask' },
  executions: { label: 'Executions', icon: 'i-ph-clock-counter-clockwise' },
  studies: { label: 'Studies', icon: 'i-ph-notebook' },
  batches: { label: 'Batches', icon: 'i-ph-arrows-split' },
  analyses: { label: 'Analyses', icon: 'i-ph-chart-bar' },
  datasets: { label: 'Datasets', icon: 'i-ph-database' },
  agents: { label: 'Agents', icon: 'i-ph-ghost' },
  prompts: { label: 'Prompts', icon: 'i-ph-chat-text' },
  models: { label: 'Models', icon: 'i-ph-cpu' },
  settings: { label: 'Settings', icon: 'i-ph-gear' },
  new: { label: 'New', icon: 'i-ph-plus' },
}

const breadcrumbs = computed(() => {
  if (relativePath.value === '/')
    return [{ label: 'Dashboard', icon: 'i-ph-squares-four' }]

  const paths = relativePath.value.split('/').filter(Boolean)
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
  <UDashboardNavbar :ui="{ root: 'sm:px-4 gap-3 print:hidden', left: 'min-w-0' }">
    <template #left>
      <UBreadcrumb
        :items="breadcrumbs"
        :ui="{ list: 'min-w-0', item: 'min-w-0', link: 'text-sm min-w-0', linkLabel: 'truncate max-w-[40ch]', separatorIcon: 'size-3.5 text-dimmed' }"
      />
    </template>

    <template #right>
      <!-- Pages teleport their primary actions here (see BasePageContent) -->
      <div id="page-actions" class="flex items-center gap-2" />
    </template>
  </UDashboardNavbar>
</template>
