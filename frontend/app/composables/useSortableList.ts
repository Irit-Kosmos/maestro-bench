import type { MaybeRefOrGetter } from 'vue'
import Sortable from 'sortablejs'

interface SortableListOptions {
  /** Reports a drop: the item at `from` now belongs at `to` */
  onMove: (from: number, to: number) => void
  /** CSS selector of the grip inside each item; only it starts a drag, so inputs and buttons stay usable */
  handle?: string
  disabled?: MaybeRefOrGetter<boolean>
}

/**
 * Drag-and-drop reordering for the direct children of a v-for list.
 *
 * The library moves DOM nodes by itself, which Vue knows nothing about. On drop the node is put
 * back where it was and `onMove` updates the data, so Vue stays the one that renders the new order.
 * Give the items a stable `:key`, not their index, so the move reuses their nodes.
 */
export function useSortableList(container: Ref<HTMLElement | null>, options: SortableListOptions) {
  let sortable: Sortable | null = null

  function destroy() {
    sortable?.destroy()
    sortable = null
  }

  watch(container, (element) => {
    destroy()
    if (!element)
      return
    sortable = Sortable.create(element, {
      handle: options.handle ?? '[data-drag-handle]',
      animation: 150,
      easing: 'cubic-bezier(0.23, 1, 0.32, 1)',
      // The clone is styled by the app (see .sortable-drag), not the browser's drag image
      forceFallback: true,
      ghostClass: 'sortable-ghost',
      dragClass: 'sortable-drag',
      disabled: toValue(options.disabled) ?? false,
      onEnd: ({ item, from, oldIndex, newIndex }) => {
        if (oldIndex === undefined || newIndex === undefined || oldIndex === newIndex)
          return
        from.removeChild(item)
        from.insertBefore(item, from.children[oldIndex] ?? null)
        options.onMove(oldIndex, newIndex)
      },
    })
  }, { immediate: true, flush: 'post' })

  watch(() => toValue(options.disabled), (disabled) => {
    sortable?.option('disabled', disabled ?? false)
  })

  onBeforeUnmount(destroy)
}
