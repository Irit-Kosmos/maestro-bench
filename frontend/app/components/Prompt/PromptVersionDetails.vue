<script setup lang="ts">
interface Props {
  promptVersion: {
    version: string
    is_default?: boolean
    is_active?: boolean
    created_at?: string
    system_prompt?: string | null
    user_prompt?: string | null
    variables?: string | null
    notes?: string | null
    prompt?: {
      name?: string
      description?: string | null
      category?: string | null
    }
  }
  showHeader?: boolean
  showMetadata?: boolean
  headerSize?: 'sm' | 'md' | 'lg'
}

const props = withDefaults(defineProps<Props>(), {
  showHeader: true,
  showMetadata: true,
  headerSize: 'md',
})

const variableNames = computed(() => parseVariables(props.promptVersion.variables || ''))
</script>

<template>
  <div class="space-y-6">
    <!-- Header with version info -->
    <div v-if="showHeader && promptVersion.prompt?.name" class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-sm font-medium text-default mb-2">
          Prompt Name
        </label>
        <p class="text-sm text-toned">
          {{ promptVersion.prompt.name }}
        </p>
      </div>
      <div>
        <label class="block text-sm font-medium text-default mb-2">
          Version
        </label>
        <PromptVersionHeader
          :version="promptVersion.version"
          :is-default="promptVersion.is_default"
          :is-active="promptVersion.is_active"
          :size="headerSize"
        />
      </div>
    </div>

    <!-- Description -->
    <div v-if="promptVersion.prompt?.description">
      <label class="block text-sm font-medium text-default mb-2">
        Description
      </label>
      <p class="text-sm text-toned">
        {{ promptVersion.prompt.description }}
      </p>
    </div>

    <!-- System Prompt -->
    <PromptContentDisplay
      v-if="promptVersion.system_prompt"
      label="System prompt"
      :content="promptVersion.system_prompt"
      :variables="variableNames"
      type="code"
    />

    <!-- User Prompt -->
    <PromptContentDisplay
      v-if="promptVersion.user_prompt"
      label="User prompt"
      :content="promptVersion.user_prompt"
      :variables="variableNames"
      type="code"
    />

    <!-- Variables -->
    <PromptVariablesDisplay
      v-if="promptVersion.variables"
      :variables="promptVersion.variables"
    />

    <!-- Notes -->
    <PromptContentDisplay
      v-if="promptVersion.notes"
      label="Notes"
      :content="promptVersion.notes"
      type="text"
    />

    <!-- Metadata -->
    <PromptMetadata
      v-if="showMetadata"
      :created-at="promptVersion.created_at"
      :category="promptVersion.prompt?.category"
      :prompt-name="promptVersion.prompt?.name"
    />
  </div>
</template>
