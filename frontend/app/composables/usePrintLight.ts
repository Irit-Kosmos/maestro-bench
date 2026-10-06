/**
 * Paper is white: print always uses the light theme, whatever is on screen.
 * Swaps the class around the print dialog, so it also covers Ctrl/Cmd+P and leaves the saved preference untouched.
 * Also flags the print state so the charts can switch to their fixed print width (see `usePrinting`).
 */
export function usePrintLight() {
  const { printing } = usePrinting()
  let restoreDark = false

  function beforePrint() {
    const root = document.documentElement
    restoreDark = root.classList.contains('dark')
    root.classList.remove('dark')
    printing.value = true
  }

  function afterPrint() {
    if (restoreDark)
      document.documentElement.classList.add('dark')
    restoreDark = false
    printing.value = false
  }

  onMounted(() => {
    window.addEventListener('beforeprint', beforePrint)
    window.addEventListener('afterprint', afterPrint)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('beforeprint', beforePrint)
    window.removeEventListener('afterprint', afterPrint)
  })
}
