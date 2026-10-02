import { defineConfig } from 'vitest/config'

// Only the pure utilities are unit tested: no Nuxt runtime needed
export default defineConfig({
  test: {
    include: ['app/**/*.test.ts'],
    environment: 'node',
  },
})
