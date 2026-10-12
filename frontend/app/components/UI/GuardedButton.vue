<script setup lang="ts">
import type { WorkspaceRole } from '~/types'

// A button for an action that needs a role. Out of reach, it stays visible but disabled, and a tooltip says
// why, so nobody wonders where the function went. Everything else goes to the underlying UButton.
defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  requires?: WorkspaceRole
  /** The action is still allowed in an archived workspace (stopping something, say) */
  archivedOk?: boolean
}>(), {
  requires: 'editor',
  archivedOk: false,
})

const { denial, workspace } = useCurrentWorkspace()
// Behind a public link there is nothing to do but read: the action is not there, instead of there and refused
const { isShared } = useShare()
const reason = computed(() => props.archivedOk
  ? denialReason(workspace.value && { ...workspace.value, archived: false }, props.requires)
  : denial(props.requires))
// In a tooltip group (the top bar), the group's shared tooltip says why
const inGroup = inject(tooltipGroupKey, false)
</script>

<template>
  <template v-if="isShared" />
  <UTooltip v-else-if="reason" :text="reason" :disabled="inGroup">
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
