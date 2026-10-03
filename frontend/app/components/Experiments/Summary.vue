<script setup lang="ts">
// What the experiment will be, and what is still missing. Each row jumps to its section.
interface Row {
  id: 'details' | 'dataset' | 'agents' | 'variations'
  label: string
  /** What is set, or what is missing */
  value: string
  done: boolean
  /** Something is set but needs fixing (as opposed to simply not started) */
  attention?: boolean
}

withDefaults(defineProps<{
  rows: Row[]
  canSubmit: boolean
  submitting: boolean
  /** What the button says: "Create and start" for one experiment, more for a batch */
  submitLabel?: string
}>(), {
  submitLabel: 'Create and start',
})

const emit = defineEmits<{
  jump: [id: Row['id']]
  submit: []
  cancel: []
}>()
</script>

<template>
  <aside aria-labelledby="summary-title" class="rounded-lg border border-default lg:sticky lg:top-0">
    <h2 id="summary-title" class="px-4 pt-4 pb-2 text-sm font-semibold text-highlighted">
      Summary
    </h2>

    <ul class="divide-y divide-default border-y border-default">
      <li v-for="row in rows" :key="row.id">
        <!-- Native button: a full-width row shouldn't inherit the press scale of UButton. Hover is instant on purpose. -->
        <button
          type="button"
          class="flex w-full items-start gap-3 px-4 py-3 text-left outline-none hover:bg-elevated/50 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-inverted"
          @click="emit('jump', row.id)"
        >
          <!-- Three shapes, so state never rests on color alone -->
          <UIcon
            :name="row.done ? 'i-ph-check-circle-bold' : row.attention ? 'i-ph-warning-bold' : 'i-ph-circle-bold'"
            class="mt-0.5 size-4 shrink-0"
            :class="row.done ? 'text-success' : row.attention ? 'text-warning' : 'text-muted'"
            aria-hidden="true"
          />
          <span class="min-w-0 flex-1">
            <span class="block text-xs text-muted">{{ row.label }}</span>
            <span
              class="mt-0.5 block text-sm text-pretty"
              :class="row.done ? 'text-highlighted' : row.attention ? 'text-warning' : 'text-muted'"
            >{{ row.value }}</span>
          </span>
        </button>
      </li>
    </ul>

    <div class="flex flex-col gap-2 p-4">
      <UTooltip :text="canSubmit ? submitLabel : 'Complete the sections above first'" :kbds="canSubmit ? ['meta', 'enter'] : undefined">
        <UButton
          block
          icon="i-ph-play-bold"
          :disabled="!canSubmit"
          :loading="submitting"
          aria-keyshortcuts="Meta+Enter Control+Enter"
          @click="emit('submit')"
        >
          {{ submitLabel }}
        </UButton>
      </UTooltip>
      <UButton block color="neutral" variant="ghost" @click="emit('cancel')">
        Cancel
      </UButton>
    </div>
  </aside>
</template>
