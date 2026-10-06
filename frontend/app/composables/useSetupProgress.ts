import type { SetupProgress } from '~/types'
import { useLocalStorage } from '@vueuse/core'

export interface SetupStep {
  id: keyof SetupProgress
  label: string
  /** Where the step is taken */
  to: string
  done: boolean
}

/**
 * The way to a first run, as a checklist drawn from what the workspace actually holds:
 * the first step not done is the current one. It goes away once complete, or when dismissed.
 */
export function useSetupProgress() {
  const { archived, canEdit } = useCurrentWorkspace()
  const { relativePath } = useWorkspace()
  const dismissed = useLocalStorage(workspaceStorageKey('maestro:setup-dismissed'), false)
  const open = useLocalStorage(workspaceStorageKey('maestro:setup-open'), true)

  const { data, refresh } = useMyLazyFetch<SetupProgress>('/setup', { key: 'setup-progress' })

  // `?new=1` opens the creation dialog of the page, for those who may create
  const create = (path: string) => canEdit.value ? `${path}?new=1` : path

  const steps = computed<SetupStep[]>(() => {
    const progress = data.value
    const all: Omit<SetupStep, 'done'>[] = [
      { id: 'provider', label: 'Connect a provider', to: '/settings' },
      { id: 'dataset', label: 'Add a dataset', to: create('/datasets') },
      { id: 'prompt', label: 'Write a prompt', to: create('/prompts') },
      { id: 'model', label: 'Register a model', to: create('/models') },
      { id: 'agent', label: 'Create an agent', to: create('/agents') },
      { id: 'experiment', label: 'Run an experiment', to: '/experiments/new' },
    ]
    return all.map(step => ({ ...step, done: !!progress?.[step.id] }))
  })

  const doneCount = computed(() => steps.value.filter(step => step.done).length)
  const current = computed(() => steps.value.find(step => !step.done))
  const visible = computed(() => !!data.value && !!current.value && !dismissed.value && !archived.value)

  // Each page can change the answer: look again as the person moves, while the list is on screen
  watch(relativePath, () => {
    if (visible.value)
      refresh()
  })

  return { steps, doneCount, current, visible, open, dismissed, refresh }
}
