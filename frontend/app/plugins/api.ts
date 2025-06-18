export default defineNuxtPlugin({
  setup() {
    const api = $fetch.create({
      baseURL: `${useRuntimeConfig().public.BACK_URL}/`,
    })

    return {
      provide: {
        api,
      },
    }
  },
})
