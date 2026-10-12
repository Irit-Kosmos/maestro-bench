<script setup lang="ts">
import type { FetchErrorKind } from '~/utils/fetchError'

interface SharedRoot {
  kind: 'experiment' | 'batch' | 'analysis' | 'study'
  item_id: number
  name: string
}

// The page of what the link points to, in the app's own page for it
const PAGES: Record<SharedRoot['kind'], string> = {
  experiment: 'experiments',
  batch: 'batches',
  analysis: 'analyses',
  study: 'studies',
}

const { token } = useShare()
const { $api } = useNuxtApp()

const error = ref<FetchErrorKind | null>(null)

onMounted(async () => {
  try {
    const root = await $api<SharedRoot>('/')
    await navigateTo(inShare(token.value!, `/${PAGES[root.kind]}/${root.item_id}`), { replace: true })
  }
  catch (e) {
    error.value = fetchErrorKind(e)
  }
})
</script>

<template>
  <BaseErrorState
    v-if="error"
    :kind="error"
    :title="error === 'not-found' ? 'This link doesn’t exist' : undefined"
    :message="error === 'not-found' ? 'Check the address, or ask for the link again.' : undefined"
    @retry="reloadNuxtApp()"
  />
  <BaseLoadingState v-else />
</template>
