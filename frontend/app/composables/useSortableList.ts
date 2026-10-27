// MAESTRO-bench: run and trace experiments with pipelines of LLM agents.
// Copyright (C) 2025-2026 Université de Toulouse, CNRS (https://www.irit.fr/)
// Copyright (C) 2025-2026 Kosmos (https://www.kosmos-education.com/)
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as published
// by the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// SPDX-License-Identifier: AGPL-3.0-or-later

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
