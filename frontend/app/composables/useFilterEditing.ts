import type { Ref } from 'vue'
import type { FilterDefinition, FilterEntry, FilterMode, FilterState, FilterValue } from '~/utils/filters'
import { emptyFilterEntry, emptyFilterState } from '~/utils/filters'

/**
 * Reading and changing the filters of a list, shared by the Filter picker and the row of chips under the toolbar.
 */
export function useFilterEditing(filters: Ref<FilterState>, definitions: () => FilterDefinition[]) {
  const entryFor = (key: string): FilterEntry => filters.value[key] ?? emptyFilterEntry()
  const selectedFor = (key: string) => entryFor(key).values

  function toggle(definition: FilterDefinition, value: FilterValue) {
    const selected = selectedFor(definition.key)
    let next: FilterValue[]
    if (definition.multiple)
      next = selected.includes(value) ? selected.filter(item => item !== value) : [...selected, value]
    else
      // Single choice: picking the selected value again clears it
      next = selected.includes(value) ? [] : [value]
    // An emptied filter disappears, so it comes back as a plain "is" next time
    const mode = next.length ? entryFor(definition.key).mode : 'include'
    filters.value = { ...filters.value, [definition.key]: { mode, values: next } }
  }

  function setMode(definition: FilterDefinition, mode: FilterMode) {
    filters.value = { ...filters.value, [definition.key]: { ...entryFor(definition.key), mode } }
  }

  function remove(definition: FilterDefinition) {
    filters.value = { ...filters.value, [definition.key]: emptyFilterEntry() }
  }

  function clearAll() {
    filters.value = emptyFilterState(definitions())
  }

  const activeDefinitions = computed(() => definitions().filter(definition => selectedFor(definition.key).length))

  return { entryFor, selectedFor, toggle, setMode, remove, clearAll, activeDefinitions }
}
