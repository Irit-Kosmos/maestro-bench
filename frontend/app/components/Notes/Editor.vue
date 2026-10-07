<script setup lang="ts">
import type { EditorHandler, EditorSuggestionMenuItem, EditorToolbarItem } from '@nuxt/ui'
import type { Editor as CoreEditor } from '@tiptap/core'
import type { EditorState } from '@tiptap/pm/state'
import type { Editor } from '@tiptap/vue-3'
import { TaskItem, TaskList } from '@tiptap/extension-list'
import { TableKit } from '@tiptap/extension-table'

// A rich-text editor for markdown, the way notes and descriptions are written: type `/` for blocks, select text for
// formatting. What it reads and writes is plain markdown, so nothing but text is ever stored.
// Without `editable` it only displays the markdown.
const props = withDefaults(defineProps<{
  editable?: boolean
  placeholder?: string
  autofocus?: boolean | 'end'
  /** Smaller type and tighter blocks, for a note shown among other things (a timeline) */
  compact?: boolean
}>(), {
  editable: true,
  placeholder: undefined,
  autofocus: false,
  compact: false,
})

const model = defineModel<string>({ default: '' })

// Tables are written as markdown tables, which have a header row and no merged cells: the editor offers no more
const extensions = [TaskList, TaskItem.configure({ nested: true }), TableKit.configure({ table: { resizable: false } })]

// What the editor does not know how to do by itself: put a table in, and change the one the cursor is in
type TableCommand = 'addRowAfter' | 'addColumnAfter' | 'deleteRow' | 'deleteColumn' | 'deleteTable'
function tableCommand(name: TableCommand): EditorHandler {
  return {
    canExecute: (editor: Editor) => editor.can()[name](),
    execute: (editor: Editor) => editor.chain().focus()[name](),
    isActive: () => false,
  }
}
const handlers = {
  table: {
    canExecute: (editor: Editor) => editor.can().insertTable(),
    execute: (editor: Editor) => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }),
    isActive: (editor: Editor) => editor.isActive('table'),
  } satisfies EditorHandler,
  addRowAfter: tableCommand('addRowAfter'),
  addColumnAfter: tableCommand('addColumnAfter'),
  deleteRow: tableCommand('deleteRow'),
  deleteColumn: tableCommand('deleteColumn'),
  deleteTable: tableCommand('deleteTable'),
}

// Shown when the cursor is in a table (the text toolbar shows when text is selected)
const tableToolbar: EditorToolbarItem<typeof handlers>[][] = [
  [
    { kind: 'addRowAfter', icon: 'i-ph-rows-plus-bottom-bold', tooltip: { text: 'Add a row below' } },
    { kind: 'addColumnAfter', icon: 'i-ph-columns-plus-right-bold', tooltip: { text: 'Add a column on the right' } },
  ],
  [
    { kind: 'deleteRow', icon: 'i-ph-minus-bold', tooltip: { text: 'Delete the row' } },
    { kind: 'deleteColumn', icon: 'i-ph-arrow-line-down-bold', tooltip: { text: 'Delete the column' } },
    { kind: 'deleteTable', icon: 'i-ph-trash-bold', color: 'error', tooltip: { text: 'Delete the table' } },
  ],
]
function inTable({ editor, state }: { editor: CoreEditor, state: EditorState }) {
  return editor.isEditable && editor.isActive('table') && state.selection.empty
}

// Shown over the selected text
const toolbar: EditorToolbarItem<typeof handlers>[][] = [
  [
    { kind: 'mark', mark: 'bold', icon: 'i-ph-text-b-bold', tooltip: { text: 'Bold' } },
    { kind: 'mark', mark: 'italic', icon: 'i-ph-text-italic-bold', tooltip: { text: 'Italic' } },
    { kind: 'mark', mark: 'strike', icon: 'i-ph-text-strikethrough-bold', tooltip: { text: 'Strikethrough' } },
    { kind: 'mark', mark: 'code', icon: 'i-ph-code-bold', tooltip: { text: 'Code' } },
  ],
  [
    { kind: 'heading', level: 2, icon: 'i-ph-text-h-two-bold', tooltip: { text: 'Heading' } },
    { kind: 'bulletList', icon: 'i-ph-list-bullets-bold', tooltip: { text: 'Bulleted list' } },
    { kind: 'taskList', icon: 'i-ph-list-checks-bold', tooltip: { text: 'Task list' } },
    { kind: 'blockquote', icon: 'i-ph-quotes-bold', tooltip: { text: 'Quote' } },
    { kind: 'link', icon: 'i-ph-link-bold', tooltip: { text: 'Link' } },
  ],
]

// Offered by `/`
const suggestions: EditorSuggestionMenuItem<typeof handlers>[][] = [
  [
    { type: 'label', label: 'Blocks' },
    { kind: 'paragraph', label: 'Text', description: 'Plain paragraph', icon: 'i-ph-text-aa-bold' },
    { kind: 'heading', level: 1, label: 'Heading 1', description: 'A big section title', icon: 'i-ph-text-h-one-bold' },
    { kind: 'heading', level: 2, label: 'Heading 2', description: 'A section title', icon: 'i-ph-text-h-two-bold' },
    { kind: 'heading', level: 3, label: 'Heading 3', description: 'A smaller title', icon: 'i-ph-text-h-three-bold' },
    { kind: 'bulletList', label: 'Bulleted list', description: 'A list of points', icon: 'i-ph-list-bullets-bold' },
    { kind: 'orderedList', label: 'Numbered list', description: 'A list of steps', icon: 'i-ph-list-numbers-bold' },
    { kind: 'taskList', label: 'Task list', description: 'Things to check off', icon: 'i-ph-list-checks-bold' },
    { kind: 'blockquote', label: 'Quote', description: 'Set a passage apart', icon: 'i-ph-quotes-bold' },
    { kind: 'table', label: 'Table', description: 'Compare runs, metrics or settings', icon: 'i-ph-table-bold' },
    { kind: 'codeBlock', label: 'Code block', description: 'A prompt, an output, a snippet', icon: 'i-ph-code-block-bold' },
    { kind: 'horizontalRule', label: 'Divider', description: 'A line between two parts', icon: 'i-ph-minus-bold' },
  ],
]

// Compact on purpose: these are notes, not documents. The theme's own sizes and side padding are for full pages
const UI = computed(() => ({
  base: [
    props.compact ? 'text-xs text-toned sm:px-0 *:my-1.5' : 'text-sm text-default sm:px-0 *:my-2.5',
    props.compact ? '[&_p]:leading-5' : '[&_p]:leading-6',
    props.compact ? '[&_h1]:text-sm [&_h2]:text-sm [&_h3]:text-xs' : '[&_h1]:text-lg [&_h2]:text-base [&_h3]:text-sm',
    '[&_pre]:text-xs/5 [&_pre]:px-3 [&_pre]:py-2',
    props.compact ? '[&_code]:text-[0.6875rem]' : '[&_code]:text-xs',
    '[&_li]:my-1',
    // Tables: a ruled grid, a tinted header, and a scroll rather than a squeeze when it is wide
    '[&_.tableWrapper]:overflow-x-auto [&_table]:my-0 [&_table]:w-full [&_table]:border-collapse',
    '[&_th]:border [&_th]:border-default [&_th]:bg-elevated/60 [&_th]:px-2 [&_th]:py-1 [&_th]:text-start [&_th]:align-top [&_th]:font-medium',
    '[&_td]:border [&_td]:border-default [&_td]:px-2 [&_td]:py-1 [&_td]:align-top',
    '[&_th>p]:my-0 [&_td>p]:my-0 [&_.selectedCell]:bg-accented/40',
    // Task lists: the checkbox sits in front of the item, and a checked item fades
    '[&_ul[data-type=taskList]]:list-none [&_ul[data-type=taskList]]:ps-0',
    '[&_ul[data-type=taskList]_li]:flex [&_ul[data-type=taskList]_li]:items-start [&_ul[data-type=taskList]_li]:gap-2 [&_ul[data-type=taskList]_li]:ps-0',
    '[&_ul[data-type=taskList]_li>label]:mt-1 [&_ul[data-type=taskList]_li>label]:shrink-0',
    '[&_ul[data-type=taskList]_li>div]:min-w-0 [&_ul[data-type=taskList]_li>div]:flex-1',
    '[&_ul[data-type=taskList]_li[data-checked=true]>div]:text-muted [&_ul[data-type=taskList]_li[data-checked=true]>div]:line-through',
  ].join(' '),
}))
</script>

<template>
  <UEditor
    v-slot="{ editor }"
    v-model="model"
    content-type="markdown"
    :editable="editable"
    :placeholder="editable ? placeholder : undefined"
    :autofocus="autofocus"
    :extensions="extensions"
    :handlers="handlers"
    :image="false"
    :mention="false"
    :ui="UI"
  >
    <template v-if="editable">
      <UEditorToolbar :editor="editor" :items="toolbar" layout="bubble" />
      <UEditorToolbar :editor="editor" :items="tableToolbar" layout="bubble" plugin-key="tableMenu" :should-show="inTable" />
      <UEditorSuggestionMenu :editor="editor" :items="suggestions" size="sm" />
    </template>
  </UEditor>
</template>
