<script setup lang="ts">
interface Props {
  label: string
  content: string
  type?: 'text' | 'code'
  /** Variable names to pick out in the text, as `{{ name }}` or `<name>` */
  variables?: readonly string[]
}

const props = withDefaults(defineProps<Props>(), {
  type: 'code',
  variables: () => [],
})

// The text cut into plain runs and variable placeholders, so the placeholders can be marked up
const segments = computed(() => {
  const names = props.variables.map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (props.type !== 'code' || names.length === 0)
    return [{ text: props.content, variable: false }]

  // Both tags of an XML slot (<name></name>) count, as does {{ name }}. Splitting on one capture group puts
  // the matches at odd indices, so the empty strings it can return must stay until the parity is read.
  const pattern = new RegExp(`(\\{\\{\\s*(?:${names.join('|')})\\s*\\}\\}|</?(?:${names.join('|')})>)`, 'g')
  return props.content
    .split(pattern)
    .map((text, index) => ({ text, variable: index % 2 === 1 }))
    .filter(segment => segment.text)
})
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
    ><template v-for="(segment, index) in segments" :key="index"><mark v-if="segment.variable" class="rounded-sm bg-primary/10 px-0.5 text-primary">{{ segment.text }}</mark><template v-else>{{ segment.text }}</template></template></pre>

    <p v-else class="whitespace-pre-wrap text-sm leading-relaxed text-toned">
      {{ content }}
    </p>
  </section>
</template>
