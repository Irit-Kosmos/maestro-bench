import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { Handle, VueFlow } from '@vue-flow/core'
import { defineNuxtPlugin } from '#app'

import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'

export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.component('VueFlow', VueFlow)
  nuxtApp.vueApp.component('VueFlowHandle', Handle)
  nuxtApp.vueApp.component('VueFlowBackground', Background)
  nuxtApp.vueApp.component('VueFlowControls', Controls)
})
