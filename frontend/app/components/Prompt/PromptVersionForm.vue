<script setup lang="ts">
export interface PromptVersionFormValues {
  version: string
  system_prompt: string
  user_prompt: string
  variables: string[]
  notes: string
  is_active: boolean
  is_default: boolean
}

// Writes a version in place of reading it: the same pane, so editing never leaves the page.
// ⌘↵ saves and Esc cancels, from any field. Textareas grow with their text, so only the pane scrolls.
// ⌘↵ is caught on the way down: a focused switch toggles on Enter whatever the modifiers, and would flip before the save.
const props = defineProps<{
  mode: 'create' | 'edit'
  saving?: boolean
}>()

const emit = defineEmits<{
  save: []
  cancel: []
}>()

const form = defineModel<PromptVersionFormValues>({ required: true })

const valid = computed(() => form.value.version.trim().length > 0)

const texts = computed(() => [form.value.system_prompt, form.value.user_prompt])

// Names written in the prompts and not listed yet: one click declares them
const detectedVariables = computed(() => undeclaredPlaceholders(texts.value, form.value.variables))
// How often the prompts use each name, to tell the unused ones from the rest
const usage = computed(() => countPlaceholders(texts.value, form.value.variables))

function addVariables(names: string[]) {
  form.value.variables = [...form.value.variables, ...names]
}

// Hovering a variable shows where the prompts use it; clicking walks through those places
interface Selectable {
  select: (start: number, end: number) => void
}
const fields = [useTemplateRef<Selectable>('systemField'), useTemplateRef<Selectable>('userField')]
const active = ref<string | null>(null)
const visits = new Map<string, number>()

function reveal(name: string) {
  const places = texts.value.flatMap((text, field) => findPlaceholders(text, form.value.variables)
    .filter(placeholder => placeholder.name === name && !placeholder.closing)
    .map(placeholder => ({ field, start: placeholder.start, end: placeholder.end })))
  if (places.length === 0)
    return
  const next = ((visits.get(name) ?? -1) + 1) % places.length
  visits.set(name, next)
  const place = places[next]!
  fields[place.field]!.value?.select(place.start, place.end)
}

function submit() {
  if (valid.value && !props.saving)
    emit('save')
}

const toggle = 'flex h-8 items-center justify-between gap-3 rounded-md border border-default px-3'
</script>

<template>
  <form
    class="flex min-h-0 flex-col"
    @submit.prevent="submit"
    @keydown.meta.enter.capture.prevent.stop="submit"
    @keydown.ctrl.enter.capture.prevent.stop="submit"
    @keydown.esc.stop="emit('cancel')"
  >
    <header class="flex h-11 shrink-0 items-center justify-between gap-3 border-b border-default px-4">
      <h2 class="truncate text-sm font-medium text-highlighted">
        {{ mode === 'create' ? 'New version' : `Edit ${form.version || 'version'}` }}
      </h2>
      <div class="flex items-center gap-2">
        <UButton type="button" color="neutral" variant="ghost" size="sm" :disabled="saving" @click="emit('cancel')">
          Cancel
          <UKbd value="esc" size="sm" />
        </UButton>
        <UButton type="submit" color="neutral" variant="soft" size="sm" :loading="saving" :disabled="!valid">
          {{ mode === 'create' ? 'Create' : 'Save' }}
          <UKbd value="meta" size="sm" /><UKbd value="enter" size="sm" />
        </UButton>
      </div>
    </header>

    <div class="min-h-0 flex-1 space-y-5 overflow-y-auto p-4">
      <div class="flex flex-wrap items-end gap-3">
        <UFormField label="Version" required class="w-full sm:w-56">
          <UInput
            v-model="form.version"
            placeholder="e.g. 2.1, v3-beta"
            autocomplete="off"
            :autofocus="mode === 'create'"
            class="w-full"
          />
        </UFormField>

        <div :class="toggle">
          <label class="text-sm text-default" for="version-active">Active</label>
          <USwitch id="version-active" v-model="form.is_active" size="sm" />
        </div>
        <div :class="toggle">
          <label class="text-sm text-default" for="version-default">Default</label>
          <USwitch id="version-default" v-model="form.is_default" size="sm" />
        </div>
      </div>

      <UFormField label="System prompt">
        <PromptTemplateField
          ref="systemField"
          v-model="form.system_prompt"
          :variables="form.variables"
          :active="active"
          :rows="4"
          placeholder="Instructions that frame the model's role"
        />
      </UFormField>

      <UFormField label="User prompt" description="Reference variables as {{ name }}, or type {{ to pick one">
        <PromptTemplateField
          ref="userField"
          v-model="form.user_prompt"
          :variables="form.variables"
          :active="active"
          :rows="8"
          placeholder="The message sent for each row"
        />
      </UFormField>

      <UFormField label="Variables" description="Names the dataset must provide for each row">
        <UInputTags v-model="form.variables" placeholder="Type a name, press Enter" class="w-full">
          <template #item-text="{ item }">
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-inverted"
              :title="usage.get(item) ? 'Show where the prompts use it' : 'Not used in the prompts'"
              @mouseenter="active = item"
              @mouseleave="active = null"
              @focus="active = item"
              @blur="active = null"
              @click="reveal(item)"
            >
              <span class="font-mono">{{ item }}</span>
              <span v-if="usage.get(item)" class="text-muted tabular-nums">{{ usage.get(item) }}×</span>
              <span v-else class="text-warning">Unused</span>
            </button>
          </template>
        </UInputTags>
        <p v-if="detectedVariables.length" class="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-warning">
          <UIcon name="i-ph-warning-bold" class="size-3.5 shrink-0" aria-hidden="true" />
          Used but not declared:
          <UButton
            v-for="name in detectedVariables"
            :key="name"
            type="button"
            size="xs"
            color="neutral"
            variant="outline"
            icon="i-ph-plus-bold"
            :label="name"
            @click="addVariables([name])"
          />
          <UButton
            v-if="detectedVariables.length > 1"
            type="button"
            size="xs"
            color="neutral"
            variant="ghost"
            label="Add all"
            @click="addVariables(detectedVariables)"
          />
        </p>
      </UFormField>

      <UFormField label="Notes">
        <UTextarea
          v-model="form.notes"
          placeholder="What changed, and why"
          autoresize
          :rows="2"
          class="w-full"
        />
      </UFormField>
    </div>
  </form>
</template>
