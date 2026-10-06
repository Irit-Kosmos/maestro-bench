<script setup lang="ts">
// The models an experiment or a run mobilises: one reads as a model (logo and name); several as
// their providers' logos overlapped, then the first model and how many more. The title lists them all.
const props = defineProps<{
  models: readonly { name: string, provider: string }[]
}>()

const distinct = computed(() => {
  const seen = new Map(props.models.map(model => [`${model.provider}/${model.name}`, model]))
  return [...seen.values()]
})

// One logo per provider, at most three: ten models from two providers are still two logos
const providers = computed(() => [...new Set(distinct.value.map(model => providerMeta(model.provider).key))].slice(0, 3))

const title = computed(() => distinct.value.map(model => `${model.name} · ${providerLabel(model.provider)}`).join('\n'))
</script>

<template>
  <span v-if="!distinct.length" class="text-dimmed">—</span>
  <ModelsLabel v-else-if="distinct.length === 1" :name="distinct[0]!.name" :provider="distinct[0]!.provider" />
  <span v-else class="inline-flex min-w-0 max-w-full items-center gap-1.5 align-middle" :title="title">
    <span class="flex shrink-0 items-center -space-x-1.5">
      <UIProviderIcon v-for="key in providers" :key="key" :provider="key" class="size-3.5" />
    </span>
    <span class="truncate">{{ distinct[0]!.name }}</span>
    <span class="shrink-0 text-dimmed tabular-nums">+{{ distinct.length - 1 }}</span>
  </span>
</template>
