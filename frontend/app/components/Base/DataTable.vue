<script setup lang="ts">
import type { DropdownMenuItem, TableColumn } from '@nuxt/ui'
import type { VNodeChild } from 'vue'
import type { WorkspaceRole } from '~/types'
import type { FilterSpec, FilterState } from '~/utils/filters'
import type { GroupRowInfo, GroupSpec, RowRenderContext } from '~/utils/groups'
import type { SortSpec, SortState } from '~/utils/sorts'
import { useVirtualizer } from '@tanstack/vue-virtual'
import { h, resolveComponent } from 'vue'
import { arrangeRows, GROUP_ROW } from '~/utils/groups'
import { activeSortSpec, sortItems } from '~/utils/sorts'

interface Column {
  key: string
  label: string
  sortable?: boolean
  class?: string
  /** Width in px. Once a column has one, the table stops sizing columns by their content (see `fixedLayout`) and
   * the columns without one share what is left; their content is truncated to fit */
  width?: number
  formatter?: (value: any, row: any) => string
  /** Rich content for the first column of a linked row (see `rowTo`); it places the row hint itself. `formatter` still feeds the search */
  render?: (row: any, hint?: string, context?: RowRenderContext) => VNodeChild
  /** Not shown, but still read by the search: for what the groups already say */
  hidden?: boolean
}

interface Action {
  label: string | ((item: any) => string)
  icon?: string
  variant?: 'solid' | 'outline' | 'ghost'
  color?: 'primary' | 'secondary' | 'success' | 'info' | 'warning' | 'error' | 'neutral'
  size?: 'xs' | 'sm' | 'md'
  handler: (item: any) => void
  show?: (item: any) => boolean
  /** The role the action needs; without it, the action is left out of the menu */
  requires?: WorkspaceRole
}

interface Props {
  data: any[]
  columns: Column[]
  actions?: Action[]
  loading?: boolean
  title?: string
  emptyMessage?: string
  searchable?: boolean
  /** Filters offered next to the search; their options are found in `data` (see `FilterSpec`) */
  filters?: FilterSpec<any>[]
  actionTo?: string
  /** Ways to cut the rows into sections, picked from a menu in the toolbar (see `v-model:group-by`) */
  groups?: GroupSpec<any>[]
  /** Things the rows can be sorted on, picked from a menu in the toolbar (see `v-model:sort-by`). Within a section when grouped */
  sorts?: SortSpec<any>[]
  /** Makes every row a link: the first column becomes the row's link, the whole row is clickable */
  rowTo?: (item: any) => string
  /** Like `rowTo`, for a row that opens something on the page (a panel) instead of going elsewhere: the first column
   * becomes a button. `rowTo` wins when both are given */
  rowOpen?: (item: any) => void
  /** Key of the row whose panel is open, to mark it in the list */
  activeKey?: string | number | null
  /** Muted text next to the first column, e.g. an id */
  rowHint?: (item: any) => string | undefined
  /** Noun used in the count, e.g. "experiment" → "12 experiments" */
  itemName?: string
  itemNamePlural?: string
  /** Total before page-level filters, so the count reads "4 of 41" */
  totalCount?: number
  /** Fills the height of its parent: toolbar and column headers stay put, only the rows scroll */
  fill?: boolean
  /** Adds a checkbox column; the toolbar turns into a selection bar (see the `selection-actions` slot) */
  selectable?: boolean
  /** Property that identifies a row in `v-model:selected` */
  rowKey?: string
  /** Virtualizes the rows so a long list stays light: only those in view are in the DOM. Needs `fill` (the rows scroll
   * inside the table) and a fixed row height in px, which every row must fit in, so no wrapping content. Section
   * headers have a height of their own (see `HEADER_HEIGHT`) */
  rowHeight?: number
}

const props = withDefaults(defineProps<Props>(), {
  actions: () => [],
  loading: false,
  title: undefined,
  emptyMessage: 'No data available',
  searchable: false,
  filters: () => [],
  groups: () => [],
  sorts: () => [],
  rowTo: undefined,
  rowOpen: undefined,
  activeKey: null,
  rowHint: undefined,
  itemName: undefined,
  itemNamePlural: undefined,
  totalCount: undefined,
  fill: false,
  selectable: false,
  rowKey: 'id',
  rowHeight: undefined,
})

const emit = defineEmits<{
  refresh: []
}>()

const UButton = resolveComponent('UButton')
const UDropdownMenu = resolveComponent('UDropdownMenu')
const NuxtLink = resolveComponent('NuxtLink')

const UCheckbox = resolveComponent('UCheckbox')
const UIcon = resolveComponent('UIcon')

const slots = useSlots()
// Every slot but the toolbar ones goes to UTable (custom cells, headers)
const tableSlots = computed(() => Object.fromEntries(Object.entries(slots).filter(([name]) => name !== 'toolbar' && name !== 'selection-actions')))

// Keys of the selected rows
const selected = defineModel<(string | number)[]>('selected', { default: () => [] })

// What is picked in the filters; bind it to seed or persist it, otherwise the table keeps it to itself
const filterState = defineModel<FilterState>('filterState', { default: () => ({}) })

// Search matches what the columns display
const { search, definitions, filtered: filteredData, hasFilters, clear: clearFilters } = useListFilters(
  () => props.data,
  () => props.filters,
  row => props.columns.map(column => renderValue(column, row[column.key], row) ?? '').join(' '),
  filterState,
)

const total = computed(() => props.totalCount ?? props.data.length)

// Key of the group spec the rows are cut by; bind it to remember the choice, otherwise the table keeps it to itself
const groupBy = defineModel<string | null>('groupBy', { default: null })
const activeGroup = computed(() => props.groups.find(group => group.key === groupBy.value) ?? null)

// Sections folded away, by id
const collapsed = ref(new Set<string>())
watch(groupBy, () => {
  collapsed.value = new Set()
})

function toggleSection(id: string) {
  const next = new Set(collapsed.value)
  if (!next.delete(id))
    next.add(id)
  collapsed.value = next
}

const sortBy = defineModel<SortState | null>('sortBy', { default: null })
const activeSort = computed(() => activeSortSpec(props.sorts, sortBy.value))
// Selection and counts read `filteredData`: sorting only changes the order the rows are shown in
const sortedData = computed(() => activeSort.value
  ? sortItems(filteredData.value, activeSort.value, sortBy.value!.direction)
  : filteredData.value)

const isGroupRow = (row: any) => !!row?.[GROUP_ROW]

// Grouped, each section is preceded by a stand-in row (see `GROUP_ROW`) that the cells draw as a header
const arranged = computed(() => activeGroup.value
  ? arrangeRows(sortedData.value, activeGroup.value, props.rowKey, collapsed.value)
  : { rows: sortedData.value as any[], trails: new Map<string | number, string[]>() })
const displayRows = computed(() => arranged.value.rows)

// The rail running down the rows of a section is drawn in its first cell, over the row (see `renderRails`)
const RAIL_STEP = 8
// Content steps in by this much for each section a row or header sits in; the checkboxes stay in line
const INDENT_STEP = 16
const railOf = (level: string) => [activeGroup.value, activeGroup.value?.then].find(found => found?.key === level)?.rail

function renderRails(trail: string[]) {
  return trail.map((level, depth) => h('span', {
    'key': level,
    'class': ['pointer-events-none absolute inset-y-0 w-0.5', railOf(level) ?? 'bg-accented'],
    'style': { left: `${depth * RAIL_STEP}px` },
    'aria-hidden': 'true',
  }))
}

const withRails = (trail: string[], content: VNodeChild) => trail.length ? h('span', { class: 'contents' }, [...renderRails(trail), content]) : content
const trailOf = (row: any) => arranged.value.trails.get(row[props.rowKey]) ?? []

const { can } = useCurrentWorkspace()
// An action the user's role cannot do is not offered at all: a row menu is no place for greyed-out items
const allowedActions = computed(() => props.actions.filter(action => !action.requires || can(action.requires)))
const hasActions = computed(() => allowedActions.value.length > 0)

// Columns sized by their content shift as rows come and go (filtering, scrolling a virtualized list), so widths are
// declared instead. Opt-in: a table that never sets a `width` keeps sizing itself
const SELECT_WIDTH = 40
const ACTIONS_WIDTH = 48
const FLEX_MIN_WIDTH = 200
const visibleColumns = computed(() => props.columns.filter(column => !column.hidden))
const fixedLayout = computed(() => visibleColumns.value.some(column => column.width))
// Below this the table scrolls sideways instead of squeezing the flexible columns to nothing
const tableMinWidth = computed(() => visibleColumns.value.reduce((sum, column) => sum + (column.width ?? FLEX_MIN_WIDTH), 0)
  + (props.selectable ? SELECT_WIDTH : 0) + (hasActions.value ? ACTIONS_WIDTH : 0))

// Virtualized rows: UTable is given only the rows in view, and two spacer rows stand in for the others. That keeps the
// table as tall as the whole list, which is what lets the header stay stuck to the top all the way down.
// A section header is shorter than a row, and the two are the only heights there are
const HEADER_HEIGHT = 36
const virtualized = computed(() => props.fill && !!props.rowHeight)
const tableEl = ref<{ $el: HTMLElement } | null>(null)
const virtualizer = useVirtualizer(computed(() => ({
  count: displayRows.value.length,
  getScrollElement: () => tableEl.value?.$el ?? null,
  estimateSize: (index: number) => isGroupRow(displayRows.value[index]) ? HEADER_HEIGHT : props.rowHeight ?? 0,
  getItemKey: (index: number) => displayRows.value[index]?.[props.rowKey] ?? index,
  overscan: 12,
  enabled: virtualized.value,
  // Something to render before the scroll area is measured, server side included
  initialRect: { width: 0, height: 800 },
})))
const virtualItems = computed(() => virtualizer.value.getVirtualItems())
const tableRows = computed(() => virtualized.value
  ? virtualItems.value.flatMap(item => displayRows.value[item.index] ?? [])
  : displayRows.value)
const spaceBefore = computed(() => virtualItems.value[0]?.start ?? 0)
const spaceAfter = computed(() => {
  const last = virtualItems.value.at(-1)
  return last ? virtualizer.value.getTotalSize() - last.end : 0
})

// The header checkbox covers every row of the list, not only those in the DOM
const allSelectedState = computed<boolean | 'indeterminate'>(() => {
  if (!selected.value.length)
    return false
  const keys = new Set(selected.value)
  return filteredData.value.every(row => keys.has(row[props.rowKey])) ? true : 'indeterminate'
})

function toggleSelectAll(value: boolean | 'indeterminate') {
  selected.value = value ? filteredData.value.map(row => row[props.rowKey]) : []
}

// A section header ticks all of its rows, the ones folded away included: they are still in the list
function groupSelectState(group: GroupRowInfo): boolean | 'indeterminate' {
  const picked = new Set(selected.value)
  const count = group.keys.filter(key => picked.has(key)).length
  return count === 0 ? false : count === group.keys.length ? true : 'indeterminate'
}

function toggleGroupSelection(group: GroupRowInfo) {
  const keys = new Set(group.keys)
  selected.value = groupSelectState(group) === true
    ? selected.value.filter(key => !keys.has(key))
    : [...selected.value, ...group.keys.filter(key => !selected.value.includes(key))]
}

// UTable tracks selection as { [rowId]: true }
const rowSelection = computed({
  get: () => Object.fromEntries(selected.value.map(key => [key, true])),
  set: (state: Record<string, boolean>) => {
    selected.value = filteredData.value
      .map(row => row[props.rowKey])
      .filter(key => state[String(key)])
  },
})

// Rows that were filtered out or deleted can't stay selected, or a bulk action would hit rows nobody sees
watch(filteredData, (rows) => {
  if (!selected.value.length)
    return
  const visible = new Set(rows.map(row => row[props.rowKey]))
  const kept = selected.value.filter(key => visible.has(key))
  if (kept.length !== selected.value.length)
    selected.value = kept
})

// What the table shows, once searched, filtered and grouped, for pages that move through it
const visibleRows = computed(() => displayRows.value.filter(row => !isGroupRow(row)))
defineExpose({ rows: visibleRows })

const selectedRows = computed(() => filteredData.value.filter(row => selected.value.includes(row[props.rowKey])))

function renderValue(col: Column, value: any, row: any) {
  return col.formatter ? col.formatter(value, row) : value
}

function menuItems(row: any): DropdownMenuItem[] {
  return allowedActions.value
    .filter(action => action.show ? action.show(row) : true)
    .map(action => ({
      label: typeof action.label === 'function' ? action.label(row) : action.label,
      icon: action.icon,
      color: action.color === 'error' ? 'error' : undefined,
      onSelect: () => action.handler(row),
    }))
}

interface CellInfo {
  row: { original: any }
}

// A row is exactly this tall, which is what the spacers rely on
function cellStyle(cell: CellInfo): Record<string, string> {
  if (isGroupRow(cell.row.original))
    return { height: `${HEADER_HEIGHT}px` }
  return virtualized.value ? { height: `${props.rowHeight}px` } : {}
}

// The first column of a row inside sections steps in with them
function indentedStyle(cell: CellInfo): Record<string, string> {
  const depth = isGroupRow(cell.row.original) ? 0 : trailOf(cell.row.original).length
  return depth ? { ...cellStyle(cell), paddingLeft: `${16 + depth * INDENT_STEP}px` } : cellStyle(cell)
}

// The row whose panel is open stays marked. Rails are drawn from the row, so grouped rows are positioned
const tableMeta = computed(() => ({
  class: {
    tr: (row: { original: any }) => {
      // A section inside another is lighter, so the outer one reads as the parent
      if (isGroupRow(row.original))
        return row.original[GROUP_ROW].trail.length ? 'relative bg-elevated/20 hover:bg-elevated/50' : 'relative bg-elevated/40 hover:bg-elevated/70'
      const active = props.activeKey != null && row.original[props.rowKey] === props.activeKey
      return [arranged.value.trails.has(row.original[props.rowKey]) && 'relative', active && 'bg-elevated/70'].filter(Boolean).join(' ')
    },
  },
}))

// A section header is one cell across the table: the leading column holds it and spans every column, the others hide
const columnCount = computed(() => visibleColumns.value.length + (props.selectable ? 1 : 0) + (hasActions.value ? 1 : 0))

// The caret and the empty space are the toggle: its ::after covers the header, and what has its own job (the box
// that ticks the section, the link to it) sits above, like the row links do
function renderGroup(group: GroupRowInfo) {
  const nested = group.trail.length > 0
  const nameClass = nested ? 'font-medium text-default' : 'font-medium text-highlighted'
  const name = group.to
    ? h(NuxtLink, {
        to: group.to,
        title: `Open ${group.label}`,
        class: ['relative z-1 min-w-0 truncate rounded-sm outline-none hover:underline focus-visible:ring-2 focus-visible:ring-inverted', nameClass],
      }, () => group.label)
    : h('span', { class: ['truncate', nameClass] }, group.label)

  return h('div', { class: 'relative flex min-w-0 items-center gap-2 px-4 text-sm', style: { height: `${HEADER_HEIGHT}px` } }, [
    ...renderRails(group.trail),
    props.selectable
      ? h(UCheckbox, {
          'modelValue': groupSelectState(group),
          'onUpdate:modelValue': () => toggleGroupSelection(group),
          'aria-label': `Select ${group.label}`,
          'class': 'relative z-1',
        })
      : null,
    h('button', {
      'type': 'button',
      'aria-expanded': !group.collapsed,
      'class': 'flex shrink-0 items-center outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-inverted',
      'style': { marginLeft: `${group.trail.length * INDENT_STEP}px` },
      'onClick': () => toggleSection(group.id),
    }, [
      h(UIcon, { 'name': 'i-ph-caret-right-bold', 'class': ['size-3.5 text-muted transition-transform duration-200 ease-(--ease-out) motion-reduce:transition-none', !group.collapsed && 'rotate-90'], 'aria-hidden': 'true' }),
      h('span', { class: 'sr-only' }, `${group.collapsed ? 'Expand' : 'Collapse'} ${group.label}`),
    ]),
    group.dot ? h('span', { 'class': ['size-2 shrink-0 rounded-full', group.dot], 'aria-hidden': 'true' }) : null,
    group.icon ? h(UIcon, { 'name': group.icon, 'class': ['size-4 shrink-0 text-muted', group.iconClass], 'aria-hidden': 'true' }) : null,
    name,
    h('span', { class: 'shrink-0 text-xs text-muted tabular-nums' }, String(group.count)),
    group.summary?.length
      ? h('span', { class: 'flex shrink-0 items-center gap-1.5 text-xs text-muted' }, group.summary.flatMap((part, i) => [
          i > 0 ? h('span', { 'class': 'text-dimmed', 'aria-hidden': 'true' }, '·') : null,
          h('span', { class: [part.class, 'tabular-nums'] }, part.label),
        ]))
      : null,
    group.hint ? h('span', { class: 'min-w-0 truncate text-xs font-normal text-dimmed' }, group.hint) : null,
  ])
}

// Convert our column format to UTable format
const tableColumns = computed<TableColumn<any>[]>(() => {
  // The leading column holds the section headers and the rails: the checkboxes' when there are some, the first one otherwise
  const leads = (index: number) => index === 0 && !props.selectable
  const cols: TableColumn<any>[] = visibleColumns.value.map((col, index) => ({
    accessorKey: col.key,
    header: col.label,
    cell: ({ row }) => {
      const group = row.original[GROUP_ROW] as GroupRowInfo | undefined
      if (group)
        return leads(index) ? renderGroup(group) : null
      const value = renderValue(col, row.getValue(col.key), row.original)
      const trail = leads(index) ? trailOf(row.original) : []
      if (index !== 0 || !(props.rowTo || props.rowOpen))
        return withRails(trail, value)

      // Stretched link: the ::after covers the row, so the whole row is one target
      const hint = props.rowHint?.(row.original)
      const linkClass = 'flex items-baseline gap-2 min-w-0 font-medium text-highlighted outline-none after:absolute after:inset-0 focus-visible:after:ring-2 focus-visible:after:ring-inset focus-visible:after:ring-inverted'
      const wrap = (children: VNodeChild, className = '') => props.rowTo
        ? h(NuxtLink, { to: props.rowTo(row.original), class: [linkClass, className] }, () => children)
        // Native button, which the table's own row click leaves alone
        : h('button', { type: 'button', class: [linkClass, 'w-full text-left', className], onClick: () => props.rowOpen?.(row.original) }, [children])

      let wrapped = false
      const rendered = col.render?.(row.original, hint, {
        trail: trailOf(row.original),
        target: (children, className) => {
          wrapped = true
          return wrap(children, className)
        },
      }) ?? [
        h('span', { class: 'truncate' }, value),
        hint ? h('span', { class: 'shrink-0 text-xs font-normal text-dimmed tabular-nums' }, hint) : null,
      ]
      return withRails(trail, wrapped ? rendered : wrap(rendered))
    },
    meta: {
      class: {
        td: (cell: CellInfo) => isGroupRow(cell.row.original) ? (leads(index) ? 'p-0' : 'hidden') : (col.class ?? ''),
      },
      colspan: {
        td: (cell: CellInfo) => isGroupRow(cell.row.original) && leads(index) ? String(columnCount.value) : '1',
      },
      style: {
        th: col.width ? { width: `${col.width}px` } : undefined,
        td: index === 0 ? indentedStyle : cellStyle,
      },
    },
  }))

  if (props.selectable) {
    cols.unshift({
      id: 'select',
      header: () => h(UCheckbox, {
        'modelValue': allSelectedState.value,
        'onUpdate:modelValue': toggleSelectAll,
        'aria-label': 'Select all rows',
      }),
      cell: ({ row }) => row.original[GROUP_ROW]
        ? renderGroup(row.original[GROUP_ROW])
        : withRails(trailOf(row.original), h(UCheckbox, {
            'modelValue': row.getIsSelected(),
            'onUpdate:modelValue': (value: boolean | 'indeterminate') => row.toggleSelected(!!value),
            'aria-label': 'Select row',
            // Above the row's stretched link, so ticking doesn't open the row
            'class': 'relative z-1',
          })),
      meta: {
        class: {
          th: 'w-10 pe-0',
          td: (cell: CellInfo) => isGroupRow(cell.row.original) ? 'p-0' : 'w-10 pe-0',
        },
        colspan: {
          td: (cell: CellInfo) => isGroupRow(cell.row.original) ? String(columnCount.value) : '1',
        },
        style: { td: cellStyle },
      },
    })
  }

  if (hasActions.value) {
    cols.push({
      id: 'actions',
      header: () => h('span', { class: 'sr-only' }, 'Actions'),
      cell: ({ row }) => {
        if (isGroupRow(row.original))
          return null
        const items = menuItems(row.original)
        if (!items.length)
          return null
        return h(UDropdownMenu, { items, content: { align: 'end' } }, () =>
          h(UButton, {
            'icon': 'i-ph-dots-three-bold',
            'color': 'neutral',
            'variant': 'ghost',
            'size': 'sm',
            'class': 'relative z-1',
            'aria-label': 'Row actions',
          }))
      },
      meta: {
        class: {
          th: 'w-12',
          // The button is wider than what px-4 leaves in 48px: clipped by the fixed layout's overflow-hidden, the cell
          // would draw a stray text-ellipsis dot next to it
          td: (cell: CellInfo) => isGroupRow(cell.row.original) ? 'hidden' : 'w-12 px-2 text-right overflow-visible text-clip',
        },
        style: { td: cellStyle },
      },
    })
  }

  return cols
})
</script>

<template>
  <div class="flex flex-col rounded-lg border border-default overflow-hidden" :class="fill && 'flex-1 min-h-0'">
    <!-- Selection bar -->
    <div v-if="selectable && selected.length" class="flex shrink-0 items-center gap-2 px-2 h-11 border-b border-default bg-elevated/50">
      <span class="px-2 text-sm font-medium text-highlighted tabular-nums">
        {{ selected.length }} selected
      </span>
      <slot name="selection-actions" :rows="selectedRows" />
      <UButton
        variant="ghost"
        color="neutral"
        icon="i-ph-x-bold"
        size="sm"
        class="ms-auto"
        @click="selected = []"
      >
        Clear
      </UButton>
    </div>

    <!-- Toolbar -->
    <BaseListToolbar
      v-else
      v-model:search="search"
      v-model:filters="filterState"
      :definitions="definitions"
      :total="total"
      :shown="filteredData.length"
      :item-name="itemName"
      :item-name-plural="itemNamePlural"
      :title="title"
      :searchable="searchable"
      :loading="loading"
      @refresh="emit('refresh')"
    >
      <!-- Page-specific filters -->
      <slot name="toolbar" />

      <template v-if="groups.length || sorts.length" #group>
        <BaseGroupMenu v-if="groups.length" v-model="groupBy" :groups="groups" />
        <BaseSortMenu v-if="sorts.length" v-model="sortBy" :sorts="sorts" />
      </template>
    </BaseListToolbar>

    <!-- Empty State -->
    <div v-if="!loading && filteredData.length === 0" class="p-6" :class="fill && 'flex-1 min-h-0 overflow-y-auto'">
      <BaseEmptyState
        :title="hasFilters ? 'No matching rows' : 'Nothing here yet'"
        :message="hasFilters ? 'Try another search, or clear the filters.' : emptyMessage"
        :icon="hasFilters ? 'i-ph-magnifying-glass-bold' : 'i-ph-folder-open-bold'"
        :action-label="hasFilters ? 'Clear filters' : undefined"
        action-icon="i-ph-x-bold"
        @action="clearFilters"
      />
    </div>

    <!-- UTable -->
    <UTable
      v-else
      ref="tableEl"
      v-model:row-selection="rowSelection"
      :data="tableRows"
      :columns="tableColumns"
      :get-row-id="(row: any) => String(row[rowKey])"
      :loading="loading"
      :empty="emptyMessage"
      class="min-w-full"
      :class="fill && 'flex-1 min-h-0'"
      :sticky="fill"
      :meta="tableMeta"
      :style="fixedLayout ? { '--table-min-width': `${tableMinWidth}px` } : undefined"
      :ui="{
        base: fixedLayout ? 'w-full min-w-(--table-min-width) table-fixed' : '',
        // Opaque when sticky, so rows don't show through while scrolling under it
        thead: fill ? 'bg-muted' : 'bg-muted/60',
        // Virtualized, the separators are drawn inside the cells: a border would add to the fixed row height
        tbody: virtualized ? 'divide-y-0' : '',
        th: 'px-4 py-2 text-xs font-medium text-muted',
        tr: rowTo || rowOpen ? 'relative hover:bg-elevated/50' : '',
        td: ['px-4 py-2.5 text-sm text-toned', fixedLayout && 'overflow-hidden text-ellipsis', virtualized && 'shadow-[inset_0_-1px_0_var(--ui-border)]'],
      }"
    >
      <!-- Stand-ins for the rows above and below the ones in the DOM -->
      <template v-if="virtualized" #body-top>
        <tr v-if="spaceBefore > 0" aria-hidden="true">
          <td :colspan="tableColumns.length" class="p-0" :style="{ height: `${spaceBefore}px` }" />
        </tr>
      </template>
      <template v-if="virtualized" #body-bottom>
        <tr v-if="spaceAfter > 0" aria-hidden="true">
          <td :colspan="tableColumns.length" class="p-0" :style="{ height: `${spaceAfter}px` }" />
        </tr>
      </template>

      <!-- Forward all dynamic slots to UTable -->
      <template v-for="(_, slotName) in tableSlots" :key="slotName" #[slotName]="slotProps">
        <!-- Section headers are drawn by the cells above, which hold no data for a custom cell to read -->
        <slot v-if="!isGroupRow(slotProps?.row?.original)" :name="slotName" v-bind="slotProps" />
      </template>
    </UTable>
  </div>
</template>
