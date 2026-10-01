<script setup lang="ts">
import type { DashboardActivity } from '~/types'

// What happened lately, and what is running now. Cells are separated by 1px of the border
// color showing through the grid gap, so the dividers stay even when the grid wraps.
const props = defineProps<{
  activity?: DashboardActivity | null
  loading?: boolean
}>()

const days = computed(() => props.activity?.days ?? 7)
const active = computed(() => props.activity?.active ?? 0)

const cell = 'flex flex-col gap-1.5 bg-default px-4 py-3'
const label = 'flex items-baseline gap-1.5 text-xs font-medium text-muted'
const value = 'h-7 flex items-center text-xl font-semibold text-highlighted tabular-nums leading-none'
</script>

<template>
  <div class="grid grid-cols-2 lg:grid-cols-4 gap-px rounded-lg border border-default bg-(--ui-border) overflow-hidden">
    <NuxtLink
      to="/experiments"
      class="outline-none hover:bg-elevated/50 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary"
      :class="cell"
    >
      <span :class="label">Running now</span>
      <span :class="value">
        <USkeleton v-if="loading" class="h-5 w-8" />
        <template v-else>
          <span :class="active ? 'text-info' : 'text-highlighted'">{{ active }}</span>
          <span
            v-if="active"
            class="ms-2 size-1.5 rounded-full bg-info motion-safe:animate-pulse"
            aria-hidden="true"
          />
        </template>
      </span>
    </NuxtLink>

    <div :class="cell">
      <span :class="label">Experiments <span class="font-normal text-dimmed">{{ days }} days</span></span>
      <span :class="value">
        <USkeleton v-if="loading" class="h-5 w-10" />
        <template v-else>{{ (activity?.experiments ?? 0).toLocaleString('en-US') }}</template>
      </span>
    </div>

    <div :class="cell">
      <span :class="label">Tokens <span class="font-normal text-dimmed">{{ days }} days</span></span>
      <span :class="value">
        <USkeleton v-if="loading" class="h-5 w-14" />
        <template v-else>{{ formatTokens(activity?.total_tokens ?? 0) }}</template>
      </span>
    </div>

    <div :class="cell">
      <span :class="label">Spend <span class="font-normal text-dimmed">{{ days }} days</span></span>
      <span :class="value">
        <USkeleton v-if="loading" class="h-5 w-16" />
        <template v-else>{{ formatCost(activity?.total_cost_usd ?? 0) }}</template>
      </span>
    </div>
  </div>
</template>
