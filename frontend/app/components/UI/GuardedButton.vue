<script setup lang="ts">
import type { WorkspaceRole } from '~/types'

// A button for an action that needs a role. Out of reach, it stays visible but disabled, and a tooltip says
// why, so nobody wonders where the function went. Everything else goes to the underlying UButton.
defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  requires?: WorkspaceRole
}>(), {
  requires: 'editor',
})

const { denial } = useCurrentWorkspace()
const reason = computed(() => denial(props.requires))
// In a tooltip group (the top bar), the group's shared tooltip says why
const inGroup = inject(tooltipGroupKey, false)
</script>

<template>
  <UTooltip v-if="reason" :text="reason" :disabled="inGroup">
    <!-- A disabled button swallows hover: the wrapper is what the tooltip listens to -->
    <span class="inline-flex" tabindex="0" :data-tooltip="inGroup ? reason : undefined">
      <UButton v-bind="{ ...$attrs, onClick: undefined, to: undefined }" disabled>
        <slot />
      </UButton>
    </span>
  </UTooltip>
  <UButton v-else v-bind="$attrs">
    <slot />
  </UButton>
</template>
