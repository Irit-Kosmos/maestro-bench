/**
 * Keep the `dark` / `light` class of `<html>` on the color mode's value.
 * The head script sets the class from the OS scheme it sees at load; the color mode plugin then
 * reads the scheme again and may land on the other one (the scheme changed in between, as when a
 * browser applies an emulated or synced theme) without touching the class. The page then shows dark
 * while the value says light, so picking Light changes nothing and it takes a second pick to apply.
 */
export default defineNuxtPlugin(() => {
  const colorMode = useColorMode()

  watch(() => colorMode.value, (value) => {
    const root = document.documentElement
    root.classList.toggle('dark', value === 'dark')
    root.classList.toggle('light', value === 'light')
  }, { immediate: true })
})
