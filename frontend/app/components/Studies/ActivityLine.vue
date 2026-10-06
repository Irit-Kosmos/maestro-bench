<script setup lang="ts">
import type { StudyActivityEvent } from '~/types'

// One line of the timeline that is not a note: something was added to the study, or an experiment of it completed
const props = defineProps<{
  event: StudyActivityEvent
}>()

const { formatDate, formatRelativeDate } = useUIHelpers()

const kind = computed(() => props.event.item ? ITEM_KINDS[props.event.item.kind] : null)
</script>

<template>
  <p v-if="event.item && kind" class="flex items-center gap-2 px-1 text-xs text-muted">
    <UIcon :name="kind.icon" class="size-3.5 shrink-0 text-dimmed" aria-hidden="true" />
    <span class="min-w-0 truncate">
      <template v-if="event.type === 'item_added'">
        <span class="font-medium text-toned">{{ event.actor?.display_name ?? 'Someone' }}</span>
        {{ ' ' }}added {{ kind.label.toLowerCase() }}{{ ' ' }}
      </template>
      <template v-else>
        {{ kind.label }}{{ ' ' }}
      </template>
      <NuxtLink
        :to="itemPath(event.item.kind, event.item.item_id)"
        class="rounded font-medium text-toned outline-none hover:text-highlighted focus-visible:ring-2 focus-visible:ring-inverted"
      >
        {{ event.item.name }}
      </NuxtLink>
      <template v-if="event.type === 'experiment_completed'">
        {{ ' ' }}completed
      </template>
    </span>
    <span class="ms-auto shrink-0" :title="formatDate(event.at)">{{ formatRelativeDate(event.at) }}</span>
  </p>
</template>
