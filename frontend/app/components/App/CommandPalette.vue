<script setup lang="ts">
import type { CommandPaletteGroup } from '@nuxt/ui'
import type { Batch, Dataset, Experiment, Prompt } from '~/types'

const { data: experiments } = await useMyLazyFetch<Experiment[]>('/experiments')
const { data: batches } = await useMyLazyFetch<Batch[]>('/batches')
const { data: datasets } = await useMyLazyFetch<Dataset[]>('/datasets')
const { data: prompts } = await useMyLazyFetch<Prompt[]>('/prompts')

const router = useRouter()

function navigate(path: string) {
  router.push(path)
}

const groups = computed<CommandPaletteGroup[]>(() => {
  const items: CommandPaletteGroup[] = []

  items.push({
    id: 'navigation',
    label: 'Navigation',
    items: [
      { label: 'Dashboard', icon: 'i-lucide-layout-dashboard', kbds: ['G', 'H'], onSelect: () => navigate('/') },
      { label: 'Experiments', icon: 'i-lucide-flask-conical', kbds: ['G', 'E'], onSelect: () => navigate('/experiments') },
      { label: 'Batches', icon: 'i-lucide-split', kbds: ['G', 'B'], onSelect: () => navigate('/batches') },
      { label: 'Analyses', icon: 'i-lucide-chart-column', kbds: ['G', 'N'], onSelect: () => navigate('/analyses') },
      { label: 'Datasets', icon: 'i-lucide-database', kbds: ['G', 'D'], onSelect: () => navigate('/datasets') },
      { label: 'Agents', icon: 'i-lucide-bot', kbds: ['G', 'A'], onSelect: () => navigate('/agents') },
      { label: 'Prompts', icon: 'i-lucide-message-square-text', kbds: ['G', 'P'], onSelect: () => navigate('/prompts') },
      { label: 'Models', icon: 'i-lucide-cpu', kbds: ['G', 'M'], onSelect: () => navigate('/models') },
    ],
  })

  items.push({
    id: 'actions',
    label: 'Actions',
    items: [
      { label: 'New Experiment', icon: 'i-lucide-plus', suffix: 'Create a new experiment', onSelect: () => navigate('/experiments/new') },
      { label: 'New Analysis', icon: 'i-lucide-plus', suffix: 'Compare executions to a ground truth', onSelect: () => navigate('/analyses/new') },
    ],
  })

  if (experiments.value?.length) {
    items.push({
      id: 'experiments',
      label: 'Experiments',
      items: experiments.value.slice(0, 20).map(exp => ({
        label: exp.name,
        icon: 'i-lucide-flask-conical',
        suffix: exp.description || undefined,
        onSelect: () => navigate(`/experiments/${exp.id}`),
      })),
    })
  }

  if (batches.value?.length) {
    items.push({
      id: 'batches',
      label: 'Batches',
      items: batches.value.slice(0, 20).map(batch => ({
        label: batch.name,
        icon: 'i-lucide-split',
        suffix: `${batch.experiments.length} experiments`,
        onSelect: () => navigate(`/batches/${batch.id}`),
      })),
    })
  }

  if (datasets.value?.length) {
    items.push({
      id: 'datasets',
      label: 'Datasets',
      items: datasets.value.slice(0, 20).map(ds => ({
        label: ds.name,
        icon: 'i-lucide-database',
        suffix: ds.description || undefined,
        onSelect: () => navigate(`/datasets/${ds.id}`),
      })),
    })
  }

  if (prompts.value?.length) {
    items.push({
      id: 'prompts',
      label: 'Prompts',
      items: prompts.value.slice(0, 20).map(p => ({
        label: p.name,
        icon: 'i-lucide-message-square-text',
        suffix: p.description || undefined,
        onSelect: () => navigate(`/prompts/${p.id}`),
      })),
    })
  }

  return items
})
</script>

<template>
  <UDashboardSearch
    :groups="groups"
    :color-mode="false"
    placeholder="Search or jump to..."
    :fuse="{ fuseOptions: { threshold: 0.3, keys: ['label', 'suffix'] }, resultLimit: 10 }"
  />
</template>
