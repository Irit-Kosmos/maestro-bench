<script setup lang="ts">
import type { Placeholder, PlaceholderSegment } from '~/utils/promptPlaceholders'

interface Props {
  label: string
  content: string
  type?: 'text' | 'code'
  /** Declared variable names to pick out in the text, as `{{ name }}` or `<name>`; other `{{ name }}` are flagged */
  variables?: readonly string[]
  /** Variable shown stronger, while it is looked at elsewhere */
  active?: string | null
}

const props = withDefaults(defineProps<Props>(), {
  type: 'code',
  variables: () => [],
  active: null,
})

// The text cut into plain runs and variable placeholders, so the placeholders can be marked up
const segments = computed<PlaceholderSegment[]>(() => props.type === 'code'
  ? splitPlaceholders(props.content, props.variables)
  : [{ text: props.content }])

function markClass(placeholder: Placeholder) {
  if (!placeholder.declared)
    return 'bg-warning/15 text-warning underline decoration-wavy underline-offset-2'
  return placeholder.name === props.active ? 'bg-primary/25 text-primary' : 'bg-primary/10 text-primary'
}

function markTitle(placeholder: Placeholder) {
  return placeholder.declared ? undefined : `${placeholder.name} is not declared as a variable`
}
</script>

<template>
  <section>
    <div class="mb-1.5 flex h-6 items-center justify-between">
      <h3 class="text-xs font-medium text-muted">
        {{ label }}
      </h3>
      <UICopyButton v-if="type === 'code'" :text="content" :label="label.toLowerCase()" />
    </div>

    <pre
      v-if="type === 'code'"
      class="whitespace-pre-wrap break-words rounded-md border border-default bg-muted/50 px-3 py-2.5 font-mono text-[13px] leading-relaxed text-highlighted"
    ><template v-for="(segment, index) in segments" :key="index"><mark v-if="segment.placeholder" class="rounded-sm px-0.5 transition-colors duration-100" :class="markClass(segment.placeholder)" :title="markTitle(segment.placeholder)">{{ segment.text }}</mark><template v-else>{{ segment.text }}</template></template></pre>

    <p v-else class="whitespace-pre-wrap text-sm leading-relaxed text-toned">
      {{ content }}
    </p>
  </section>
</template>
