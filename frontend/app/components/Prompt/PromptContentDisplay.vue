<script setup lang="ts">
interface Props {
  label: string
  content: string
  type?: 'text' | 'code'
}

withDefaults(defineProps<Props>(), {
  type: 'code',
})
</script>

<template>
  <div>
    <label class="block text-sm font-medium text-neutral-700 mb-3">
      {{ label }}
    </label>
    <div v-if="type === 'code'" class="bg-white rounded-lg p-4 border border-neutral-200">
      <pre class="text-sm text-neutral-800 font-mono whitespace-pre-wrap leading-relaxed">{{ content }}</pre>
    </div>
    <div v-else class="bg-white rounded-lg p-4 border border-neutral-200">
      <p class="text-sm text-neutral-600 leading-relaxed">
        {{ content }}
      </p>
    </div>
  </div>
</template>
