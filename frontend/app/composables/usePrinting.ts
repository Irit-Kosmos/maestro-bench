// Half a portrait sheet's content width (A4 or Letter, 14mm margins), minus the card padding and the gap
const PRINT_CHART_WIDTH = 296

/**
 * Unovis charts size themselves from the screen layout and don't re-measure for the sheet,
 * so while printing they get a fixed width that fits two per row.
 */
export function usePrinting() {
  const printing = useState('printing', () => false)

  /** Width for a chart's `width` prop: fixed while printing, `undefined` (autosize) otherwise */
  const chartWidth = computed(() => printing.value ? PRINT_CHART_WIDTH : undefined)

  const nextFrame = () => new Promise(resolve => requestAnimationFrame(() => resolve(undefined)))

  /** Resize the charts, let them redraw (Unovis draws in the next frame), then open the print dialog */
  async function print() {
    printing.value = true
    await nextTick()
    await nextFrame()
    await nextFrame()
    window.print()
  }

  return { printing, chartWidth, print }
}
