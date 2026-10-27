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

type CellValues = Record<string, unknown>

interface DatasetRowsResponse {
  file_type: 'csv' | 'json'
  headers: string[]
  rows: CellValues[]
  total_rows: number
  revision: string
  read_only_reason: string | null
}

export interface EditorRow {
  /** Stable across edits, adds and deletes; the row's position isn't */
  key: number
  values: CellValues
  /** The row as last loaded or saved; null for a row added since */
  original: CellValues | null
  /** Lowercased text of the whole row, built on first search */
  haystack: string | null
}

/** What a cell shows and what editing it starts from */
export function cellText(value: unknown): string {
  if (value === null || value === undefined)
    return ''
  if (typeof value === 'object')
    return JSON.stringify(value)
  return String(value)
}

/** Objects and arrays can't be edited as text */
export function isEditableCell(value: unknown): boolean {
  return typeof value !== 'object' || value === null
}

// Edited text keeps the type of the value it replaces, so a JSON number stays a number
function coerceCellValue(text: string, reference: unknown): unknown {
  if (typeof reference === 'number') {
    const parsed = Number(text)
    return text.trim() !== '' && Number.isFinite(parsed) ? parsed : text
  }
  if (typeof reference === 'boolean') {
    if (text === 'true')
      return true
    if (text === 'false')
      return false
  }
  if (reference === null && text === '')
    return null
  return text
}

const MIN_COLUMN_WIDTH = 96
const MAX_COLUMN_WIDTH = 360
const WIDTH_SAMPLE_ROWS = 200
const SEARCH_DELAY_MS = 150

/**
 * Whole-file editing state for a dataset: every row is loaded once, edits stay
 * in memory as a draft, and saving writes the file back.
 */
export function useDatasetEditor(datasetId: Ref<number>) {
  const { $api } = useNuxtApp()

  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  const fileType = ref<'csv' | 'json'>('csv')
  const headers = shallowRef<string[]>([])
  // Why the file itself can't be written back; on top of that, the user's role may not allow it either
  const fileReadOnlyReason = ref<string | null>(null)
  const { denial } = useCurrentWorkspace()
  const readOnlyReason = computed(() => fileReadOnlyReason.value ?? denial('editor'))
  const columnWidths = shallowRef<number[]>([])
  const revision = ref('')

  const rows = shallowRef<EditorRow[]>([])
  // Rows as last loaded or saved, in file order: what "discard" returns to
  let baseline: CellValues[] = []
  let nextKey = 0

  // Cells are edited in place, so views that show them track `version`
  const version = ref(0)
  const changedCells = new Map<number, Set<string>>()
  const editedCellCount = ref(0)
  const addedRowCount = ref(0)
  const deletedRowCount = ref(0)

  const selected = shallowRef<Set<number>>(new Set())

  const query = ref('')
  const appliedQuery = ref('')
  let searchTimer: ReturnType<typeof setTimeout> | undefined

  const changeCount = computed(() => editedCellCount.value + addedRowCount.value + deletedRowCount.value)
  const isDirty = computed(() => changeCount.value > 0)
  const isReadOnly = computed(() => readOnlyReason.value !== null)

  const displayedRows = computed(() => {
    const needle = appliedQuery.value.trim().toLowerCase()
    if (!needle)
      return rows.value
    return rows.value.filter(row => rowHaystack(row).includes(needle))
  })

  function rowHaystack(row: EditorRow): string {
    row.haystack ??= headers.value.map(h => cellText(row.values[h])).join('\n').toLowerCase()
    return row.haystack
  }

  watch(query, (value) => {
    clearTimeout(searchTimer)
    if (!value.trim()) {
      appliedQuery.value = ''
      return
    }
    searchTimer = setTimeout(() => {
      appliedQuery.value = value
    }, SEARCH_DELAY_MS)
  })

  function clearSearch() {
    clearTimeout(searchTimer)
    query.value = ''
    appliedQuery.value = ''
  }

  function buildRow(original: CellValues): EditorRow {
    return { key: nextKey++, values: { ...original }, original, haystack: null }
  }

  function applyBaseline(source: CellValues[]) {
    baseline = source
    rows.value = source.map(buildRow)
    changedCells.clear()
    editedCellCount.value = 0
    addedRowCount.value = 0
    deletedRowCount.value = 0
    selected.value = new Set()
    version.value++
  }

  function measureColumns() {
    const sample = rows.value.slice(0, WIDTH_SAMPLE_ROWS)
    columnWidths.value = headers.value.map((header) => {
      let longest = header.length
      for (const row of sample)
        longest = Math.max(longest, Math.min(cellText(row.values[header]).length, 60))
      return Math.min(MAX_COLUMN_WIDTH, Math.max(MIN_COLUMN_WIDTH, longest * 7.5 + 28))
    })
  }

  async function load() {
    loading.value = true
    error.value = null
    try {
      const response = await $api<DatasetRowsResponse>(`/datasets/${datasetId.value}/rows`)
      fileType.value = response.file_type
      headers.value = response.headers
      fileReadOnlyReason.value = response.read_only_reason
      revision.value = response.revision
      clearSearch()
      applyBaseline(response.rows)
      measureColumns()
    }
    catch (e: any) {
      console.error('Error loading dataset rows:', e)
      error.value = e?.data?.detail || 'Failed to load the dataset'
    }
    finally {
      loading.value = false
    }
  }

  function setCell(row: EditorRow, header: string, text: string) {
    const previous = row.values[header]
    const next = coerceCellValue(text, row.original?.[header] ?? previous)
    if (Object.is(previous, next))
      return

    row.values[header] = next
    row.haystack = null

    if (row.original) {
      let changed = changedCells.get(row.key)
      if (Object.is(row.original[header], next)) {
        if (changed?.delete(header)) {
          editedCellCount.value--
          if (!changed.size)
            changedCells.delete(row.key)
        }
      }
      else if (!changed?.has(header)) {
        if (!changed)
          changedCells.set(row.key, changed = new Set())
        changed.add(header)
        editedCellCount.value++
      }
    }
    version.value++
  }

  function isCellChanged(row: EditorRow, header: string): boolean {
    void version.value
    return changedCells.get(row.key)?.has(header) ?? false
  }

  function addRow(): EditorRow {
    // A blank row never matches a search, so show everything to keep it in view
    clearSearch()
    const values: CellValues = {}
    for (const header of headers.value)
      values[header] = ''
    const row: EditorRow = { key: nextKey++, values, original: null, haystack: null }
    rows.value = [...rows.value, row]
    addedRowCount.value++
    version.value++
    return row
  }

  function deleteRows(keys: Set<number>) {
    if (!keys.size)
      return
    rows.value = rows.value.filter((row) => {
      if (!keys.has(row.key))
        return true
      if (row.original) {
        deletedRowCount.value++
        editedCellCount.value -= changedCells.get(row.key)?.size ?? 0
        changedCells.delete(row.key)
      }
      else {
        addedRowCount.value--
      }
      return false
    })
    selected.value = new Set([...selected.value].filter(key => !keys.has(key)))
    version.value++
  }

  function deleteSelected() {
    deleteRows(selected.value)
  }

  function toggleSelected(row: EditorRow) {
    const next = new Set(selected.value)
    if (!next.delete(row.key))
      next.add(row.key)
    selected.value = next
  }

  function selectAllDisplayed() {
    selected.value = new Set(displayedRows.value.map(row => row.key))
  }

  function clearSelection() {
    selected.value = new Set()
  }

  function discard() {
    applyBaseline(baseline)
  }

  async function save() {
    if (saving.value || isReadOnly.value)
      return { success: false as const }

    saving.value = true
    try {
      const response = await $api<{ revision: string, total_rows: number }>(`/datasets/${datasetId.value}/rows`, {
        method: 'PUT',
        body: { rows: rows.value.map(row => row.values), revision: revision.value },
      })
      revision.value = response.revision

      // What was just written is the new baseline; rows keep their keys
      for (const row of rows.value)
        row.original = { ...row.values }
      baseline = rows.value.map(row => row.original!)
      changedCells.clear()
      editedCellCount.value = 0
      addedRowCount.value = 0
      deletedRowCount.value = 0
      version.value++
      return { success: true as const }
    }
    catch (e: any) {
      console.error('Error saving dataset rows:', e)
      return {
        success: false as const,
        conflict: e?.statusCode === 409 || e?.status === 409,
        message: e?.data?.detail || 'Failed to save the dataset',
      }
    }
    finally {
      saving.value = false
    }
  }

  onScopeDispose(() => clearTimeout(searchTimer))

  return {
    // State
    loading,
    saving,
    error,
    fileType,
    headers,
    columnWidths,
    readOnlyReason,
    isReadOnly,
    rows,
    displayedRows,
    version,
    selected,
    query,
    appliedQuery,
    changeCount,
    editedCellCount,
    addedRowCount,
    deletedRowCount,
    isDirty,

    // Actions
    load,
    save,
    discard,
    setCell,
    isCellChanged,
    addRow,
    deleteRows,
    deleteSelected,
    toggleSelected,
    selectAllDisplayed,
    clearSelection,
    clearSearch,
  }
}

export type DatasetEditor = ReturnType<typeof useDatasetEditor>
