<script setup lang="ts">
import type { Experiment } from '~/types'

interface NavItem {
  label: string
  icon: string
  to: string
  kbds: string[]
}

const { relativePath } = useWorkspace()
const { canEdit } = useCurrentWorkspace()
const collapsed = ref(false)

const { data: experiments } = await useMyLazyFetch<Experiment[]>('/experiments')

const sections: { label?: string, items: NavItem[] }[] = [
  {
    items: [
      { label: 'Dashboard', icon: 'i-ph-squares-four', to: '/', kbds: ['G', 'H'] },
    ],
  },
  {
    label: 'Evaluation',
    items: [
      { label: 'Experiments', icon: 'i-ph-flask', to: '/experiments', kbds: ['G', 'E'] },
      { label: 'Batches', icon: 'i-ph-arrows-split', to: '/batches', kbds: ['G', 'B'] },
      { label: 'Executions', icon: 'i-ph-clock-counter-clockwise', to: '/executions', kbds: ['G', 'X'] },
      { label: 'Analyses', icon: 'i-ph-chart-bar', to: '/analyses', kbds: ['G', 'N'] },
    ],
  },
  {
    label: 'Library',
    items: [
      { label: 'Datasets', icon: 'i-ph-database', to: '/datasets', kbds: ['G', 'D'] },
      { label: 'Prompts', icon: 'i-ph-chat-text', to: '/prompts', kbds: ['G', 'P'] },
      { label: 'Models', icon: 'i-ph-cpu', to: '/models', kbds: ['G', 'M'] },
      { label: 'Agents', icon: 'i-ph-ghost', to: '/agents', kbds: ['G', 'A'] },
    ],
  },
]

const recentExperiments = computed(() =>
  [...(experiments.value || [])]
    .sort((a, b) => parseApiDate(b.created_at).getTime() - parseApiDate(a.created_at).getTime())
    .slice(0, 5),
)

function isActive(to: string) {
  return to === '/' ? relativePath.value === '/' : relativePath.value.startsWith(to)
}

const itemClass = 'group flex items-center gap-2 h-8 px-2 rounded-md text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted'

// Same key as Linear: the fastest users toggle the sidebar without the mouse.
// No animation on purpose: a keyboard toggle should feel instant.
defineShortcuts({
  '[': () => {
    collapsed.value = !collapsed.value
  },
})
</script>

<template>
  <UDashboardSidebar
    id="main"
    v-model:collapsed="collapsed"
    resizable
    collapsible
    :min-size="200"
    :default-size="248"
    :max-size="360"
    :collapsed-size="56"
    :ui="{
      root: 'peer min-w-14 bg-muted dark:bg-(--ui-bg-sidebar) print:hidden',
      header: 'px-3',
      body: 'px-2 py-1 gap-5',
      footer: 'px-2 py-2',
      handle: 'print:hidden after:absolute after:inset-y-0 after:-left-px after:w-0.5 hover:after:bg-accented peer-data-[dragging=true]:after:bg-primary',
    }"
  >
    <template #header="{ collapsed: isCollapsed }">
      <AppWorkspaceSwitcher v-if="!isCollapsed" />

      <UTooltip
        :text="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :kbds="['[']"
        :content="{ side: 'right' }"
      >
        <UDashboardSidebarCollapse size="sm" :class="isCollapsed && 'mx-auto'" />
      </UTooltip>
    </template>

    <template #default="{ collapsed: isCollapsed }">
      <!-- Search + create, the two actions people reach for most -->
      <div class="flex gap-1" :class="isCollapsed ? 'flex-col items-center' : 'items-center'">
        <UDashboardSearchButton
          :collapsed="isCollapsed"
          size="sm"
          :class="isCollapsed ? '' : 'flex-1'"
        />
        <UTooltip v-if="canEdit" text="New experiment" :kbds="['C']" :content="{ side: 'right' }">
          <UButton
            to="/experiments/new"
            icon="i-ph-note-pencil"
            color="neutral"
            variant="ghost"
            size="sm"
            aria-label="New experiment"
          />
        </UTooltip>
      </div>

      <nav aria-label="Main" class="flex flex-col gap-4">
        <div
          v-for="(section, index) in sections"
          :key="section.label ?? index"
          class="flex flex-col gap-px"
        >
          <template v-if="section.label">
            <p v-if="!isCollapsed" class="px-2 pb-1 text-xs font-medium text-dimmed">
              {{ section.label }}
            </p>
            <USeparator v-else class="px-2 pb-2" />
          </template>

          <UTooltip
            v-for="item in section.items"
            :key="item.to"
            :text="item.label"
            :kbds="item.kbds"
            :disabled="!isCollapsed"
            :content="{ side: 'right' }"
          >
            <NuxtLink
              :to="item.to"
              :aria-current="isActive(item.to) ? 'page' : undefined"
              :aria-label="isCollapsed ? item.label : undefined"
              :class="[
                itemClass,
                isCollapsed && 'justify-center',
                isActive(item.to)
                  ? 'bg-accented/70 text-highlighted'
                  : 'text-toned hover:bg-elevated hover:text-highlighted',
              ]"
            >
              <UIcon
                :name="item.icon"
                class="size-4 shrink-0"
                :class="isActive(item.to) ? 'text-highlighted' : 'text-muted group-hover:text-toned'"
              />
              <span v-if="!isCollapsed" class="truncate">{{ item.label }}</span>
            </NuxtLink>
          </UTooltip>
        </div>

        <!-- Jump back into recent work without going through the list -->
        <div v-if="!isCollapsed && recentExperiments.length" class="flex flex-col gap-px">
          <p class="px-2 pb-1 text-xs font-medium text-dimmed">
            Recent experiments
          </p>
          <NuxtLink
            v-for="exp in recentExperiments"
            :key="exp.id"
            :to="`/experiments/${exp.id}`"
            :title="exp.name"
            :aria-current="relativePath === `/experiments/${exp.id}` ? 'page' : undefined"
            class="h-7 font-normal" :class="[
              itemClass,
              relativePath === `/experiments/${exp.id}`
                ? 'bg-accented/70 text-highlighted'
                : 'text-toned hover:bg-elevated hover:text-highlighted',
            ]"
          >
            <UIStatusIcon :status="exp.status" class="w-4 justify-center" />
            <span class="truncate">{{ exp.name }}</span>
          </NuxtLink>
        </div>
      </nav>
    </template>

    <template #footer="{ collapsed: isCollapsed }">
      <div class="flex w-full flex-col gap-1" :class="isCollapsed && 'items-center'">
        <AppSetupChecklist v-if="!isCollapsed" class="mb-1" />

        <!-- The account leads; the shortcuts live in its menu (and under ?) -->
        <div class="flex w-full gap-1" :class="isCollapsed ? 'flex-col items-center' : 'items-center'">
          <AppUserMenu :collapsed="isCollapsed" />

          <UTooltip text="Settings" :kbds="['G', 'S']" :content="{ side: isCollapsed ? 'right' : 'top' }">
            <UButton
              to="/settings"
              icon="i-ph-gear"
              color="neutral"
              :variant="isActive('/settings') ? 'soft' : 'ghost'"
              size="sm"
              aria-label="Settings"
              :aria-current="isActive('/settings') ? 'page' : undefined"
            />
          </UTooltip>

          <AppThemeToggle :collapsed="isCollapsed" />
        </div>
      </div>
    </template>
  </UDashboardSidebar>
</template>
