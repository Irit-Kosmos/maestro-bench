<template>
  <!-- First tooltip waits, neighbours open instantly while the pointer sweeps -->
  <UApp :tooltip="{ delayDuration: 500, skipDelayDuration: 300 }">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
  </UApp>
</template>
