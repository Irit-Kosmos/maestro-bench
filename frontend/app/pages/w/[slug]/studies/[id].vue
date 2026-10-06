<script setup lang="ts">
import type { StudyDetail } from '~/types'
import { useLocalStorage } from '@vueuse/core'
import { apiErrorMessage } from '~/composables/useAnalyses'

const route = useRoute()
const router = useRouter()
const studyId = computed(() => Number.parseInt(route.params.id as string))

const { ok, fail } = useStandardToast()
const { refreshStudies, updateStudy, deleteStudy } = useStudies()
const { canEdit } = useCurrentWorkspace()
const { formatDate } = useUIHelpers()

const { data: study, pending, error, refresh } = await useMyLazyFetch<StudyDetail>(() => `/studies/${studyId.value}`)

useBreadcrumbLabel(() => study.value?.name)
useSeoMeta({ title: () => study.value?.name ?? 'Study' })

const archived = computed(() => study.value?.status === 'archived')

// The timeline and the journal of the study stay mounted once seen, so they are told when something may have changed them
const refreshTimeline = () => refreshNuxtData(`study-activity-${studyId.value}`)
const refreshJournal = () => refreshNuxtData(`notes-study-${studyId.value}`)

// What changed may show in the lists too (the sidebar, the studies page)
async function reload() {
  await Promise.all([refresh(), refreshStudies(), refreshTimeline(), refreshJournal()])
}

// --- Tabs: kept in the address, so a link opens on the right one ---

const TABS = ['overview', 'items', 'activity'] as const
type Tab = typeof TABS[number]

const tab = computed<Tab>({
  get: () => TABS.find(name => name === route.query.tab) ?? 'overview',
  set: (value) => {
    const { tab: _tab, ...query } = route.query
    router.replace({ query: value === 'overview' ? query : { ...query, tab: value } })
  },
})

// A tab is built the first time it is opened, then only hidden: coming back to it costs no request and keeps
// where you were (a sort, a half-written note). What changes elsewhere is read again by `reload`.
const visited = reactive(new Set<Tab>([tab.value]))
watch(tab, name => visited.add(name))

const tabs = computed(() => [
  { label: 'Overview', value: 'overview', icon: 'i-ph-notebook-bold' },
  { label: 'Items', value: 'items', icon: 'i-ph-stack-bold' },
  { label: 'Activity', value: 'activity', icon: 'i-ph-pulse-bold' },
])

// --- Properties panel: ⌘I, like Linear; remembered per browser ---

const showProperties = useLocalStorage('maestro:study-properties', true)
defineShortcuts({
  meta_i: () => {
    showProperties.value = !showProperties.value
  },
})

// --- Actions ---

// The title is the field: a click on it edits it in place; Enter or leaving the field saves, Esc gives up
const renaming = ref(false)
const nameDraft = ref('')
const renameField = useTemplateRef<HTMLInputElement>('renameField')
const renamable = computed(() => canEdit.value && !archived.value)

async function startRenaming() {
  if (!renamable.value)
    return
  nameDraft.value = study.value?.name ?? ''
  renaming.value = true
  await nextTick()
  renameField.value?.focus()
  renameField.value?.select()
}
async function rename() {
  // Enter and the field losing focus both land here: the first one does it
  if (!renaming.value)
    return
  const name = nameDraft.value.trim()
  renaming.value = false
  if (!study.value || !name || name === study.value.name)
    return
  try {
    await updateStudy(studyId.value, { name })
    await refresh()
  }
  catch (e) {
    fail('Couldn’t rename the study', apiErrorMessage(e))
  }
}

async function setStatus(status: 'active' | 'archived') {
  try {
    await updateStudy(studyId.value, { status })
    await refresh()
  }
  catch (e) {
    fail('Couldn’t change the status', apiErrorMessage(e))
  }
}

const showDeleteDialog = ref(false)
const isDeleting = ref(false)
async function handleDelete() {
  isDeleting.value = true
  try {
    await deleteStudy(studyId.value)
    showDeleteDialog.value = false
    ok('Study deleted', { description: 'What it gathered was kept.' })
    await navigateTo('/studies')
  }
  catch (e) {
    fail('Couldn’t delete the study', apiErrorMessage(e))
  }
  finally {
    isDeleting.value = false
  }
}

const menu = computed(() => [
  [
    archived.value
      ? { label: 'Unarchive', icon: 'i-ph-archive-bold', onSelect: () => setStatus('active') }
      : { label: 'Archive', icon: 'i-ph-archive-bold', onSelect: () => setStatus('archived') },
  ],
  [{ label: 'Delete study', icon: 'i-ph-trash-bold', color: 'error' as const, onSelect: () => { showDeleteDialog.value = true } }],
])

const stats = computed(() => study.value
  ? [
      { label: 'Items', value: String(itemCount(study.value.counts)) },
      { label: 'Executions', value: study.value.execution_count ? String(study.value.execution_count) : '—' },
      { label: 'Tokens', value: formatTokens(study.value.total_tokens), title: formatCount(study.value.total_tokens) },
      { label: 'Cost', value: formatCost(study.value.total_cost_usd), title: formatCostPrecise(study.value.total_cost_usd) },
    ]
  : [])
</script>

<template>
  <div class="pb-6">
    <BaseLoadingState v-if="pending && !study" />
    <BaseErrorState
      v-else-if="error && !study"
      :kind="fetchErrorKind(error)"
      action-to="/studies"
      action-label="Back to studies"
      @retry="refresh()"
    />

    <div v-else-if="study" :key="study.id" class="mx-auto flex max-w-6xl flex-col gap-5">
      <AppPageActions>
        <UTooltip text="Properties" :kbds="['meta', 'I']">
          <UButton
            icon="i-ph-sidebar-simple-bold"
            color="neutral"
            :variant="showProperties ? 'soft' : 'ghost'"
            size="sm"
            :aria-pressed="showProperties"
            aria-label="Toggle the properties panel"
            @click="() => { showProperties = !showProperties }"
          />
        </UTooltip>
        <UDropdownMenu v-if="canEdit" :items="menu" :content="{ align: 'end' }">
          <UButton icon="i-ph-dots-three-bold" color="neutral" variant="ghost" size="sm" aria-label="More actions" />
        </UDropdownMenu>
      </AppPageActions>

      <UAlert
        v-if="archived"
        color="warning"
        variant="subtle"
        icon="i-ph-archive-bold"
        title="This study is archived"
        description="It is read-only: nothing can be added to it, and its notes can only be read."
        :actions="canEdit ? [{ label: 'Unarchive', color: 'neutral', variant: 'outline', onClick: () => setStatus('active') }] : undefined"
      />

      <header>
        <h1 class="flex items-center gap-2.5 text-xl font-semibold text-highlighted">
          <StudiesStatusIcon :status="study.status" size="size-5" tooltip />
          <form v-if="renaming" class="min-w-0 flex-1" @submit.prevent="rename">
            <input
              ref="renameField"
              v-model="nameDraft"
              maxlength="200"
              aria-label="Study name"
              class="-mx-1.5 w-[calc(100%+0.75rem)] rounded-md bg-elevated px-1.5 py-0.5 text-xl font-semibold text-highlighted outline-none ring-2 ring-inverted"
              @keydown.esc="renaming = false"
              @blur="rename"
            >
          </form>
          <button
            v-else-if="renamable"
            type="button"
            title="Rename"
            class="group -mx-1.5 flex min-w-0 cursor-text items-center gap-2 rounded-md px-1.5 py-0.5 text-start outline-none transition-colors hover:bg-elevated focus-visible:ring-2 focus-visible:ring-inverted"
            @click="startRenaming"
          >
            <span class="min-w-0 text-balance">{{ study.name }}</span>
            <UIcon name="i-ph-pencil-simple-bold" class="size-3.5 shrink-0 text-dimmed opacity-0 transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100" aria-hidden="true" />
          </button>
          <span v-else class="min-w-0 text-balance">{{ study.name }}</span>
        </h1>
        <div class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted">
          <UIMetaItem icon="i-ph-hash-bold" label="Study">
            {{ study.id }}
          </UIMetaItem>
          <UIMetaItem icon="i-ph-calendar-blank-bold" label="Created">
            {{ formatDate(study.created_at) }}
          </UIMetaItem>
          <UIMetaItem v-if="study.author" icon="i-ph-user-bold" label="Created by">
            {{ study.author.display_name }}
          </UIMetaItem>
        </div>
      </header>

      <UTabs
        v-model="tab"
        :items="tabs"
        :content="false"
        variant="link"
        size="sm"
        :ui="{ root: 'gap-0', list: 'gap-5 p-0', trigger: 'px-0' }"
      />

      <!-- The panel stays in the grid and its column closes to nothing: the page glides, and what is hidden is out of reach -->
      <div
        class="grid gap-y-6 transition-[grid-template-columns,column-gap] ease-(--ease-out) motion-reduce:transition-none lg:grid-cols-[minmax(0,1fr)_var(--properties-width)]"
        :class="showProperties ? 'duration-200 [--properties-width:16rem] lg:gap-x-10' : 'duration-150 [--properties-width:0rem] lg:gap-x-0'"
      >
        <div class="min-w-0">
          <div v-show="tab === 'overview'" class="flex flex-col gap-8">
            <dl class="flex flex-wrap gap-x-10 gap-y-4">
              <div v-for="stat in stats" :key="stat.label">
                <dt class="text-xs text-muted">
                  {{ stat.label }}
                </dt>
                <dd class="mt-0.5 text-lg font-semibold text-highlighted" :title="stat.title">
                  {{ stat.value }}
                </dd>
              </div>
            </dl>

            <StudiesDescription :study="study" @changed="reload" />

            <ExperimentsSection id="notes" title="Notes" icon="i-ph-notepad-bold" description="What you notice and decide as results come in.">
              <NotesJournal kind="study" :item-id="study.id" :readonly="archived" @changed="refreshTimeline" />
            </ExperimentsSection>
          </div>

          <div v-if="visited.has('items')" v-show="tab === 'items'">
            <StudiesItems :study="study" @changed="reload" />
          </div>

          <div v-if="visited.has('activity')" v-show="tab === 'activity'">
            <StudiesActivity :study-id="study.id" :readonly="archived" @changed="reload" />
          </div>
        </div>

        <div class="min-w-0 overflow-hidden" :class="!showProperties && 'max-lg:hidden'" :inert="!showProperties" :aria-hidden="!showProperties">
          <StudiesProperties
            :study="study"
            class="w-64 transition-[opacity,translate] ease-(--ease-out) motion-reduce:transition-none"
            :class="showProperties ? 'translate-x-0 opacity-100 duration-200' : 'translate-x-2 opacity-0 duration-150'"
            @changed="reload"
          />
        </div>
      </div>
    </div>

    <BaseConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete study?"
      message="Its notes are deleted with it. The experiments, batches and analyses it gathers are kept."
      confirm-label="Delete"
      variant="error"
      :loading="isDeleting"
      @confirm="handleDelete"
    />
  </div>
</template>
