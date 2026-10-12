import type { RunState } from '~/types'
import { createEventHook, createSharedComposable, useDebounceFn, useEventListener, useEventSource } from '@vueuse/core'

/**
 * State of the running executions, pushed by the backend over one connection shared by every
 * consumer. It opens with the first one and closes with the last.
 *
 * Each event carries the whole state of an execution, so what is known is always replaced,
 * never patched. Only status changes are worth a refetch: they are what `onStatus` reports.
 */
export const useLiveRuns = createSharedComposable(() => {
  const runs = reactive(new Map<number, RunState>())
  const statusChanged = createEventHook<RunState | undefined>()

  // Behind a public link there is no workspace to listen to: a page shows its state as it was loaded
  if (useShare().isShared.value)
    return { runOf: (_experimentId: number) => undefined, onStatus: statusChanged.on }

  const { eventSource, status } = useEventSource(`${useRuntimeConfig().public.BACK_URL}/workspaces/${useWorkspace().slug.value}/events`, [], { autoReconnect: true, withCredentials: true })

  for (const name of ['snapshot', 'progress', 'status'] as const) {
    useEventListener(eventSource, name, (event: MessageEvent<string>) => {
      const run: RunState = JSON.parse(event.data)
      runs.set(run.experiment_id, run)
      if (name === 'status')
        statusChanged.trigger(run)
    })
  }

  // The snapshot sent on reconnection only lists the runs still going: drop the ones that were
  // going before, and let consumers refetch what ended in the meantime
  let hasConnected = false
  watch(status, (value) => {
    if (value !== 'OPEN')
      return
    if (hasConnected) {
      for (const [id, run] of runs) {
        if (run.status === 'running' || run.status === 'queued')
          runs.delete(id)
      }
      statusChanged.trigger(undefined)
    }
    hasConnected = true
  })

  return {
    /** Latest state of an experiment's execution, once it has been seen going */
    runOf: (experimentId: number) => runs.get(experimentId),
    /** Called when an execution changes status, and without a run when the connection came back */
    onStatus: statusChanged.on,
  }
})

/** Refresh what a page lists whenever a run starts or ends; bursts (a whole batch) count once */
export function useRefreshOnRunStatus(refresh: () => unknown, delay = 300) {
  useLiveRuns().onStatus(useDebounceFn(refresh, delay))
}
