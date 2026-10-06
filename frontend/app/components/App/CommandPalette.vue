<script setup lang="ts">
import type { CommandPaletteGroup } from '@nuxt/ui'
import type { Batch, Dataset, Experiment, Prompt } from '~/types'

const { data: experiments } = await useMyLazyFetch<Experiment[]>('/experiments')
const { data: batches } = await useMyLazyFetch<Batch[]>('/batches')
const { data: datasets } = await useMyLazyFetch<Dataset[]>('/datasets')
const { data: prompts } = await useMyLazyFetch<Prompt[]>('/prompts')

const router = useRouter()
const { colorMode } = useTheme()
const icons = useAppConfig().ui.icons

const { canEdit } = useCurrentWorkspace()

const open = ref(false)

/**
 * Closes the palette, then runs the action once it has left the DOM. Switching theme or opening a page re-renders
 * most of the screen; done while the palette is still fading out, that re-render made it flash back in.
 */
function run(action: () => unknown) {
  open.value = false
  nextTick(() => requestAnimationFrame(() => action()))
}

function navigate(path: string) {
  run(() => router.push(path))
}

function setTheme(preference: 'system' | 'light' | 'dark') {
  run(() => {
    colorMode.preference = preference
  })
}

const groups = computed<CommandPaletteGroup[]>(() => {
  const items: CommandPaletteGroup[] = []

  items.push({
    id: 'navigation',
    label: 'Navigation',
    items: [
      { label: 'Dashboard', icon: 'i-ph-squares-four-bold', kbds: ['G', 'H'], onSelect: () => navigate('/') },
      { label: 'Experiments', icon: 'i-ph-flask-bold', kbds: ['G', 'E'], onSelect: () => navigate('/experiments') },
      { label: 'Executions', icon: 'i-ph-clock-counter-clockwise-bold', kbds: ['G', 'X'], onSelect: () => navigate('/executions') },
      { label: 'Batches', icon: 'i-ph-arrows-split-bold', kbds: ['G', 'B'], onSelect: () => navigate('/batches') },
      { label: 'Analyses', icon: 'i-ph-chart-bar-bold', kbds: ['G', 'N'], onSelect: () => navigate('/analyses') },
      { label: 'Datasets', icon: 'i-ph-database-bold', kbds: ['G', 'D'], onSelect: () => navigate('/datasets') },
      { label: 'Prompts', icon: 'i-ph-chat-text-bold', kbds: ['G', 'P'], onSelect: () => navigate('/prompts') },
      { label: 'Models', icon: 'i-ph-cpu-bold', kbds: ['G', 'M'], onSelect: () => navigate('/models') },
      { label: 'Agents', icon: 'i-ph-ghost-bold', kbds: ['G', 'A'], onSelect: () => navigate('/agents') },
      { label: 'Settings', icon: 'i-ph-gear-bold', kbds: ['G', 'S'], onSelect: () => navigate('/settings') },
    ],
  })

  // Creating is for editors: a viewer is not offered what the app would turn away
  if (canEdit.value) {
    items.push({
      id: 'actions',
      label: 'Actions',
      items: [
        { label: 'New experiment', icon: 'i-ph-plus-bold', suffix: 'Run agents over a dataset', onSelect: () => navigate('/experiments/new') },
        { label: 'New analysis', icon: 'i-ph-plus-bold', suffix: 'Compare executions to a ground truth', onSelect: () => navigate('/analyses/new') },
        { label: 'New dataset', icon: 'i-ph-plus-bold', suffix: 'Upload a CSV or JSON file', onSelect: () => navigate('/datasets?new=1') },
        { label: 'New prompt', icon: 'i-ph-plus-bold', suffix: 'Write a prompt and its first version', onSelect: () => navigate('/prompts?new=1') },
        { label: 'New agent', icon: 'i-ph-plus-bold', suffix: 'Pair a prompt version with a model', onSelect: () => navigate('/agents?new=1') },
        { label: 'New model', icon: 'i-ph-plus-bold', suffix: 'Register a provider’s model', onSelect: () => navigate('/models?new=1') },
      ],
    })
  }

  if (experiments.value?.length) {
    items.push({
      id: 'experiments',
      label: 'Experiments',
      items: experiments.value.slice(0, 20).map(exp => ({
        label: exp.name,
        icon: 'i-ph-flask-bold',
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
        icon: 'i-ph-arrows-split-bold',
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
        icon: 'i-ph-database-bold',
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
        icon: 'i-ph-chat-text-bold',
        suffix: p.description || undefined,
        onSelect: () => navigate(`/prompts/${p.id}`),
      })),
    })
  }

  items.push({
    id: 'theme',
    label: 'Theme',
    items: (['system', 'light', 'dark'] as const).map(preference => ({
      label: preference[0]!.toUpperCase() + preference.slice(1),
      icon: icons[preference],
      active: colorMode.preference === preference,
      onSelect: () => setTheme(preference),
    })),
  })

  return items
})
</script>

<template>
  <UDashboardSearch
    v-model:open="open"
    :groups="groups"
    :color-mode="false"
    :transition="false"
    placeholder="Search or jump to…"
    :fuse="{ fuseOptions: { threshold: 0.3, keys: ['label', 'suffix'] }, resultLimit: 10 }"
  />
</template>
