<script setup lang="ts">
import type { ProviderStatus } from '~/types'
import { apiErrorMessage } from '~/composables/useAnalyses'

const props = defineProps<{
  provider: ProviderStatus | null
}>()

const emit = defineEmits<{ saved: [provider: ProviderStatus] }>()

const open = defineModel<boolean>('open', { default: false })

const { keys } = useWorkspaceAdmin()
const { ok } = useStandardToast()

const apiKey = ref('')
const error = ref<string | null>(null)
const saving = ref(false)

const replacing = computed(() => props.provider?.source === 'workspace')

async function save() {
  if (!props.provider || !apiKey.value.trim() || saving.value)
    return
  saving.value = true
  error.value = null
  try {
    const updated = await keys.set(props.provider.provider, apiKey.value)
    ok(`${providerLabel(props.provider.provider)} key saved`)
    emit('saved', updated)
    open.value = false
  }
  catch (e) {
    error.value = (apiErrorMessage(e) ?? 'The key could not be saved')
  }
  finally {
    saving.value = false
  }
}

// Never keep a key in memory longer than the dialog
function reset() {
  apiKey.value = ''
  error.value = null
}
</script>

<template>
  <UModal v-model:open="open" @after:leave="reset">
    <template #content>
      <UCard>
        <template #header>
          <h2 class="text-lg font-semibold text-highlighted">
            {{ replacing ? 'Replace' : 'Set' }} the {{ provider ? providerLabel(provider.provider) : '' }} key
          </h2>
        </template>

        <form class="flex flex-col gap-4" @submit.prevent="save">
          <UFormField label="API key" :error="error ?? undefined">
            <UInput
              v-model="apiKey"
              type="password"
              autocomplete="off"
              spellcheck="false"
              class="w-full"
              placeholder="Paste the key"
              autofocus
            />
            <template #help>
              <span class="text-xs text-muted text-pretty">
                Stored encrypted for this workspace only. Once saved, only its last four characters are shown again.
                Its runs use this key instead of the instance’s.
              </span>
            </template>
          </UFormField>

          <div class="flex justify-end gap-3">
            <UButton color="neutral" variant="outline" type="button" @click="() => { open = false }">
              Cancel
            </UButton>
            <UButton type="submit" :disabled="!apiKey.trim()" :loading="saving">
              Save key
            </UButton>
          </div>
        </form>
      </UCard>
    </template>
  </UModal>
</template>
