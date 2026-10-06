<script setup lang="ts">
import type { PreviewValue } from '~/utils/promptPreview'

// A prompt as the model receives it: the values put into the text stand out, by where they come from.
const props = defineProps<{
  label: string
  /** The rendered text, its values between marks (see promptPreview) */
  text: string
  /** What each variable put into the text */
  values: Readonly<Record<string, PreviewValue>>
  /** Variable shown stronger, while it is looked at elsewhere */
  active?: string | null
}>()

const segments = computed(() => splitRendered(props.text))

function markClass(variable: string) {
  const kind = props.values[variable]?.kind
  const isActive = variable === props.active
  if (kind === 'missing')
    return isActive ? 'bg-warning/30 text-warning' : 'bg-warning/15 text-warning'
  if (kind === 'stand-in')
    return isActive ? 'bg-elevated text-highlighted italic underline decoration-dashed underline-offset-2' : 'bg-muted text-toned italic underline decoration-dashed underline-offset-2'
  return isActive ? 'bg-primary/25 text-primary' : 'bg-primary/10 text-primary'
}

function markTitle(variable: string) {
  const kind = props.values[variable]?.kind
  if (kind === 'missing')
    return `${variable} has no value in this row: the model receives “None”`
  if (kind === 'stand-in')
    return `${variable} is only known when the agent runs`
  return variable
}
</script>

<template>
  <section>
    <h3 class="mb-1.5 flex h-6 items-center text-xs font-medium text-muted">
      {{ label }}
    </h3>
    <pre class="whitespace-pre-wrap break-words rounded-md border border-default bg-muted/50 px-3 py-2.5 font-mono text-[13px] leading-relaxed text-highlighted"><template v-for="(segment, index) in segments" :key="index"><mark v-if="segment.variable" class="rounded-sm px-0.5 transition-colors duration-100" :class="markClass(segment.variable)" :title="markTitle(segment.variable)">{{ segment.text }}</mark><template v-else>{{ segment.text }}</template></template></pre>
  </section>
</template>
