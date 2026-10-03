<script setup lang="ts">
interface Props {
  isOpen: boolean
  promptVersionDetails: any
}

interface Emits {
  'update:isOpen': [value: boolean]
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isOpen = computed({
  get: () => props.isOpen,
  set: (value: boolean) => emit('update:isOpen', value),
})
</script>

<template>
  <UModal
    v-model:open="isOpen" :ui="{ content: 'lg:min-w-1/2' }"
  >
    <template #content>
      <UCard class="overflow-auto max-h-[80vh]">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-base font-semibold leading-6 text-highlighted">
              Prompt Details: {{ promptVersionDetails?.prompt?.name }} v{{ promptVersionDetails?.version }}
            </h3>
            <UButton color="neutral" variant="ghost" icon="i-ph-x-bold" class="-my-1" @click="() => { isOpen = false }" />
          </div>
        </template>

        <PromptVersionDetails
          v-if="promptVersionDetails"
          :prompt-version="promptVersionDetails"
          header-size="sm"
        />

        <template #footer>
          <div class="flex justify-end">
            <UButton color="neutral" variant="solid" @click="() => { isOpen = false }">
              Close
            </UButton>
          </div>
        </template>
      </UCard>
    </template>
  </UModal>
</template>
