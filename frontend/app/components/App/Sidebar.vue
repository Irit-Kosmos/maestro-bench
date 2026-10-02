<script setup lang="ts">
import type { Experiment } from '~/types'

interface NavItem {
  label: string
  icon: string
  to: string
  kbds: string[]
}

const route = useRoute()
const shortcutsOpen = useShortcutsOverlay()
const collapsed = ref(false)

const { data: experiments } = await useMyLazyFetch<Experiment[]>('/experiments')

const sections: { label?: string, items: NavItem[] }[] = [
  {
    items: [
      { label: 'Dashboard', icon: 'i-lucide-layout-dashboard', to: '/', kbds: ['G', 'H'] },
      { label: 'Experiments', icon: 'i-lucide-flask-conical', to: '/experiments', kbds: ['G', 'E'] },
      { label: 'Batches', icon: 'i-lucide-split', to: '/batches', kbds: ['G', 'B'] },
      { label: 'Analyses', icon: 'i-lucide-chart-column', to: '/analyses', kbds: ['G', 'N'] },
      { label: 'Datasets', icon: 'i-lucide-database', to: '/datasets', kbds: ['G', 'D'] },
    ],
  },
  {
    label: 'Configuration',
    items: [
      { label: 'Agents', icon: 'i-lucide-bot', to: '/agents', kbds: ['G', 'A'] },
      { label: 'Prompts', icon: 'i-lucide-message-square-text', to: '/prompts', kbds: ['G', 'P'] },
      { label: 'Models', icon: 'i-lucide-cpu', to: '/models', kbds: ['G', 'M'] },
      { label: 'Settings', icon: 'i-lucide-settings', to: '/settings', kbds: ['G', 'S'] },
    ],
  },
]

const recentExperiments = computed(() =>
  [...(experiments.value || [])]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5),
)

function isActive(to: string) {
  return to === '/' ? route.path === '/' : route.path.startsWith(to)
}

const itemClass = 'group flex items-center gap-2 h-8 px-2 rounded-md text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-primary'

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
      root: 'peer min-w-14 bg-muted dark:bg-(--ui-bg-sidebar)',
      header: 'px-3',
      body: 'px-2 py-1 gap-5',
      footer: 'px-2 py-2',
      handle: 'after:absolute after:inset-y-0 after:-left-px after:w-0.5 hover:after:bg-accented peer-data-[dragging=true]:after:bg-primary',
    }"
  >
    <template #header="{ collapsed: isCollapsed }">
      <NuxtLink
        v-if="!isCollapsed"
        to="/"
        class="flex items-center gap-2 min-w-0 flex-1 h-8 px-1 rounded-md outline-none hover:bg-elevated focus-visible:ring-2 focus-visible:ring-primary"
      >
        <img
          src="/MAESTRO-bench.png"
          alt=""
          class="shrink-0 h-6 w-auto translate-y-px"
        >
        <span class="text-sm font-semibold leading-none translate-y-0.5 text-highlighted truncate">MAESTRO-bench</span>
      </NuxtLink>

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
        <UTooltip text="New experiment" :kbds="['C']" :content="{ side: 'right' }">
          <UButton
            to="/experiments/new"
            icon="i-lucide-square-pen"
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
                :class="isActive(item.to) ? 'text-primary' : 'text-muted group-hover:text-toned'"
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
            :aria-current="route.path === `/experiments/${exp.id}` ? 'page' : undefined"
            class="h-7 font-normal" :class="[
              itemClass,
              route.path === `/experiments/${exp.id}`
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
      <div class="flex w-full gap-1" :class="isCollapsed ? 'flex-col items-center' : 'items-center'">
        <UTooltip
          text="Keyboard shortcuts"
          :kbds="['?']"
          :disabled="!isCollapsed"
          :content="{ side: 'right' }"
        >
          <UButton
            icon="i-lucide-keyboard"
            color="neutral"
            variant="ghost"
            size="sm"
            :block="!isCollapsed"
            :aria-label="isCollapsed ? 'Keyboard shortcuts' : undefined"
            :class="isCollapsed ? '' : 'flex-1 justify-start text-muted'"
            @click="() => { shortcutsOpen = true }"
          >
            <template v-if="!isCollapsed">
              <span class="flex-1 text-start">Shortcuts</span>
              <UKbd value="?" size="sm" />
            </template>
          </UButton>
        </UTooltip>

        <AppThemeToggle :collapsed="isCollapsed" />
      </div>
    </template>
  </UDashboardSidebar>
</template>
