/**
 * Swap themes in a single frame. Without this, every element with a color
 * transition (buttons, links, rows) fades on its own schedule, so the page
 * briefly shows a mix of both themes. The theme icon opts out via
 * `data-theme-icon` so its own crossfade still plays.
 */
export default defineNuxtPlugin(() => {
  const colorMode = useColorMode()

  watch(() => colorMode.value, () => {
    const style = document.createElement('style')
    style.textContent = '*:not([data-theme-icon]),*::before,*::after{transition:none!important}'
    document.head.appendChild(style)

    // Flush styles with transitions off, then restore them next tick
    void window.getComputedStyle(document.body).opacity
    setTimeout(() => style.remove(), 1)
  }, { flush: 'post' })
})
