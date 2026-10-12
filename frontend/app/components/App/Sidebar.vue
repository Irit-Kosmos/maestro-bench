<script setup lang="ts">
interface NavItem {
  label: string
  icon: string
  to: string
  kbds: string[]
}

const { relativePath } = useWorkspace()
const { canEdit } = useCurrentWorkspace()
const collapsed = ref(false)

const { studies } = useStudies()

const sections: { label?: string, items: NavItem[] }[] = [
  {
    items: [
      { label: 'Dashboard', icon: 'i-ph-squares-four', to: '/', kbds: ['G', 'H'] },
      { label: 'Studies', icon: 'i-ph-notebook', to: '/studies', kbds: ['G', 'Y'] },
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

// The studies being worked on, the most recently touched first: a way back into them without the list
const MAX_STUDIES = 5
const activeStudies = computed(() => studies.value.filter(study => study.status === 'active').slice(0, MAX_STUDIES))

function isActive(to: string) {
  return to === '/' ? relativePath.value === '/' : relativePath.value.startsWith(to)
}

const itemClass = 'group flex items-center gap-2 h-8 px-2 rounded-md text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-inverted'

// ⌘B like VS Code rather than Linear's `[`, which needs AltGr on an AZERTY keyboard.
// No animation on purpose: a keyboard toggle should feel instant.
defineShortcuts({
  meta_b: () => {
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
        :kbds="['meta', 'B']"
        :content="{ side: 'right' }"
      >
        <UDashboardSidebarCollapse size="sm" :class="isCollapsed && 'mx-auto'" />
      </UTooltip>
    </template>

    <template #default="{ collapsed: isCollapsed }">
      <!-- The command palette stays on ⌘K; the sidebar keeps a single primary action -->
      <UTooltip v-if="canEdit" text="New experiment" :kbds="['C']" :content="{ side: 'right' }">
        <UButton
          to="/experiments/new"
          icon="i-ph-note-pencil"
          color="neutral"
          variant="subtle"
          size="sm"
          :block="!isCollapsed"
          :label="isCollapsed ? undefined : 'New experiment'"
          :class="isCollapsed && 'mx-auto'"
          aria-label="New experiment"
        />
      </UTooltip>

      <nav aria-label="Main" class="flex flex-col gap-4">
        <template v-for="(section, index) in sections" :key="section.label ?? index">
          <div class="flex flex-col gap-px">
            <template v-if="section.label">
              <p v-if="!isCollapsed" class="px-2 pb-1 text-xs font-medium text-muted">
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

          <!-- The studies in progress, right under the entry that leads to all of them -->
          <div v-if="index === 0 && !isCollapsed && activeStudies.length" class="-mt-3.5 ms-4 flex flex-col gap-px border-s border-default ps-1">
            <NuxtLink
              v-for="study in activeStudies"
              :key="study.id"
              :to="`/studies/${study.id}`"
              :title="study.name"
              :aria-current="relativePath === `/studies/${study.id}` ? 'page' : undefined"
              class="h-7 font-normal" :class="[
                itemClass,
                relativePath === `/studies/${study.id}`
                  ? 'bg-accented/70 text-highlighted'
                  : 'text-toned hover:bg-elevated hover:text-highlighted',
              ]"
            >
              <StudiesStatusIcon :status="study.status" class="w-4 justify-center" />
              <span class="truncate">{{ study.name }}</span>
            </NuxtLink>
          </div>
        </template>
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
