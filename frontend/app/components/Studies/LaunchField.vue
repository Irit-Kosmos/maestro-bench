<script setup lang="ts">
import type { Study } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

// The studies a new experiment or batch is put in once it starts. Nothing is saved here: the page does it
// when it launches, so leaving the form leaves the studies as they were (except one made from this field).
const model = defineModel<number[]>({ default: () => [] })

const { studies, createStudy } = useStudies()
const { fail } = useStandardToast()

const chosen = computed(() => model.value
  .map(id => studies.value.find(study => study.id === id))
  .filter((study): study is Study => !!study))

const open = ref(false)
const creating = ref(false)

function toggle(study: Study) {
  model.value = model.value.includes(study.id)
    ? model.value.filter(id => id !== study.id)
    : [...model.value, study.id]
}

async function create(name: string) {
  creating.value = true
  try {
    const study = await createStudy({ name })
    model.value = [...model.value, study.id]
  }
  catch (error) {
    fail('Couldn’t create the study', apiErrorMessage(error))
  }
  finally {
    creating.value = false
  }
}
</script>

<template>
  <UFormField label="Studies" hint="Optional">
    <div class="flex flex-wrap items-center gap-1.5">
      <span
        v-for="study in chosen"
        :key="study.id"
        class="inline-flex h-7 max-w-56 items-center gap-1.5 rounded-md border border-default ps-2 pe-1 text-sm text-toned"
      >
        <StudiesStatusIcon :status="study.status" />
        <span class="truncate">{{ study.name }}</span>
        <button
          type="button"
          :aria-label="`Remove from ${study.name}`"
          class="flex size-5 cursor-pointer items-center justify-center rounded text-dimmed outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default"
          @click="toggle(study)"
        >
          <UIcon name="i-ph-x-bold" class="size-3" aria-hidden="true" />
        </button>
      </span>

      <UPopover v-model:open="open" :content="{ align: 'start', sideOffset: 6, collisionPadding: 16 }" :ui="{ content: 'overflow-hidden' }">
        <button
          type="button"
          class="inline-flex h-7 cursor-pointer items-center gap-1.5 rounded-md border border-dashed border-accented px-2 text-sm text-muted outline-none transition-colors hover:bg-elevated hover:text-default focus-visible:bg-elevated focus-visible:text-default data-[state=open]:bg-elevated data-[state=open]:text-default"
        >
          <UIcon name="i-ph-plus-bold" class="size-3.5" aria-hidden="true" />
          {{ chosen.length ? 'Study' : 'Add to a study' }}
        </button>

        <template #content>
          <StudiesPicker :selected="model" :creating="creating" @toggle="toggle" @create="create" />
        </template>
      </UPopover>
    </div>
  </UFormField>
</template>
