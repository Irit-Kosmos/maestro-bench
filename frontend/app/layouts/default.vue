<script setup lang="ts">
</script>

<template>
  <div class="w-screen h-screen max-w-6xl m-auto px-4 ">
    <nav class="flex gap-4 items-center py-4 justify-between ">
      <span class="text-2xl font-bold">
        <NuxtLink to="/">maestro-bench</NuxtLink>
      </span>

      <div class="flex items-center gap-4">
        <!-- Navigation Links -->
        <div class="flex items-center gap-2">
          <UButton
            to="/"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:home"
          >
            Dashboard
          </UButton>
          <UButton
            to="/experiments"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:flask-conical"
          >
            Experiments
          </UButton>
          <UButton
            to="/datasets"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:database"
          >
            Datasets
          </UButton>
          <UButton
            to="/agents"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:users"
          >
            Agents
          </UButton>
        </div>
      </div>
    </nav>
    <slot />
  </div>
</template>
