<script setup lang="ts">
</script>

<template>
  <div class="w-screen h-screen max-w-6xl m-auto px-4 ">
    <nav class="flex gap-4 items-center py-4 justify-between ">
      <span class="text-2xl font-bold">
        <NuxtLink to="/">
          <span class="hidden lg:inline">maestro-bench</span>
          <span class="inline lg:hidden">mb</span>
        </NuxtLink>
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
            <span class="hidden lg:inline">Dashboard</span>
          </UButton>
          <UButton
            to="/experiments"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:flask-conical"
          >
            <span class="hidden lg:inline">Experiments</span>
          </UButton>
          <UButton
            to="/datasets"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:database"
          >
            <span class="hidden lg:inline">Datasets</span>
          </UButton>
          <UButton
            to="/agents"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:users"
          >
            <span class="hidden lg:inline">Agents</span>
          </UButton>
          <UButton
            to="/prompts"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:message-square-text"
          >
            <span class="hidden lg:inline">Prompts</span>
          </UButton>
          <UButton
            to="/models"
            variant="ghost"
            color="neutral"
            size="sm"
            icon="i-lucide:cpu"
          >
            <span class="hidden lg:inline">Models</span>
          </UButton>
        </div>
      </div>
    </nav>
    <slot />
  </div>
</template>
