<script setup lang="ts">
// UKbd renders arrows as text glyphs, which fall back to another font and sit off-center in the key
const props = defineProps<{ value: string }>()

const ICONS: Record<string, string> = {
  'enter': 'i-ph-arrow-elbow-down-left-bold',
  '↑': 'i-ph-arrow-up-bold',
  '↓': 'i-ph-arrow-down-bold',
  '←': 'i-ph-arrow-left-bold',
  '→': 'i-ph-arrow-right-bold',
}

const icon = computed(() => ICONS[props.value])
</script>

<template>
  <UKbd v-if="icon" size="sm" class="align-middle">
    <UIcon :name="icon" class="size-2.5" />
  </UKbd>
  <UKbd v-else :value="value" size="sm" class="align-middle" />
</template>
