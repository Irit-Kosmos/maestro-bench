/** Light / dark helpers on top of Nuxt UI's color mode (`preference` is light, dark or system). */
export function useTheme() {
  const colorMode = useColorMode()
  const isDark = computed(() => colorMode.value === 'dark')

  /** Flip whatever is on screen; this settles `system` into an explicit choice. */
  function toggle() {
    colorMode.preference = isDark.value ? 'light' : 'dark'
  }

  return { colorMode, isDark, toggle }
}
