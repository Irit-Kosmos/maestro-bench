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
    <label class="block text-sm font-medium text-default mb-3">
      {{ label }}
    </label>
    <div v-if="type === 'code'" class="bg-default rounded-lg p-4 border border-default">
      <pre class="text-sm text-highlighted font-mono whitespace-pre-wrap leading-relaxed">{{ content }}</pre>
    </div>
    <div v-else class="bg-default rounded-lg p-4 border border-default">
      <p class="text-sm text-toned leading-relaxed">
        {{ content }}
      </p>
    </div>
  </div>
</template>
