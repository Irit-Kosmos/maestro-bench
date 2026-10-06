<script setup lang="ts">
import type { StudyDetail } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const emit = defineEmits<{
  created: [study: StudyDetail]
}>()

const open = defineModel<boolean>('open', { default: false })

const { createStudy } = useStudies()
const { showCreateSuccess, showCreateError } = useStandardToast()

const name = ref('')
const isCreating = ref(false)
const valid = computed(() => name.value.trim().length > 0)

async function submit() {
  if (!valid.value)
    return
  isCreating.value = true
  try {
    const study = await createStudy({ name: name.value.trim() })
    showCreateSuccess('Study')
    open.value = false
    emit('created', study)
  }
  catch (error) {
    showCreateError('Study', apiErrorMessage(error))
  }
  finally {
    isCreating.value = false
  }
}
</script>

<template>
  <BaseCrudModal
    v-model:open="open"
    title="Study"
    mode="create"
    :loading="isCreating"
    :disabled="!valid"
    @submit="submit"
    @after-leave="name = ''"
  >
    <UFormField label="Name" required help="A theme to gather experiments, batches and analyses around, e.g. “Does prompt v3 beat v2?”">
      <UInput v-model="name" class="w-full" autofocus maxlength="200" placeholder="Study name" />
    </UFormField>
  </BaseCrudModal>
</template>
