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

// Names written as {{ name }} in the prompts and not listed yet: one click declares them
const detectedVariables = computed(() => {
  const found = new Set<string>()
  for (const text of [form.value.system_prompt, form.value.user_prompt]) {
    for (const match of text.matchAll(/\{\{\s*([A-Z_]\w*)\s*\}\}/gi))
      found.add(match[1]!)
  }
  return [...found].filter(name => !form.value.variables.includes(name))
})

function addVariables(names: string[]) {
  form.value.variables = [...form.value.variables, ...names]
}

function submit() {
  if (valid.value && !props.saving)
    emit('save')
}

const fieldUi = { base: 'font-mono text-[13px] leading-relaxed' }
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
        <UTextarea
          v-model="form.system_prompt"
          placeholder="Instructions that frame the model's role"
          autoresize
          :rows="4"
          :ui="fieldUi"
          class="w-full"
        />
      </UFormField>

      <UFormField label="User prompt" description="Reference variables as {{ name }}">
        <UTextarea
          v-model="form.user_prompt"
          placeholder="The message sent for each row"
          autoresize
          :rows="8"
          :ui="fieldUi"
          class="w-full"
        />
      </UFormField>

      <UFormField label="Variables" description="Names the dataset must provide for each row">
        <UInputTags v-model="form.variables" placeholder="Type a name, press Enter" class="w-full" />
        <p v-if="detectedVariables.length" class="mt-2 flex flex-wrap items-center gap-1.5 text-xs text-muted">
          Found in the prompts:
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
