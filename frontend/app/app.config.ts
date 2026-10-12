export default defineAppConfig({
  ui: {
    colors: {
      primary: 'indigo',
      neutral: 'slate',
    },
    // Nuxt UI's built-in icons (chevrons, close, loading…) default to Lucide: point them at Phosphor
    icons: {
      arrowDown: 'i-ph-arrow-down-bold',
      arrowLeft: 'i-ph-arrow-left-bold',
      arrowRight: 'i-ph-arrow-right-bold',
      arrowUp: 'i-ph-arrow-up-bold',
      caution: 'i-ph-warning-circle-bold',
      check: 'i-ph-check-bold',
      chevronDoubleLeft: 'i-ph-caret-double-left-bold',
      chevronDoubleRight: 'i-ph-caret-double-right-bold',
      chevronDown: 'i-ph-caret-down-bold',
      chevronLeft: 'i-ph-caret-left-bold',
      chevronRight: 'i-ph-caret-right-bold',
      chevronUp: 'i-ph-caret-up-bold',
      close: 'i-ph-x-bold',
      copy: 'i-ph-copy-bold',
      copyCheck: 'i-ph-check-bold',
      dark: 'i-ph-moon-bold',
      drag: 'i-ph-dots-six-vertical-bold',
      ellipsis: 'i-ph-dots-three-bold',
      error: 'i-ph-x-circle-bold',
      external: 'i-ph-arrow-up-right-bold',
      eye: 'i-ph-eye-bold',
      eyeOff: 'i-ph-eye-slash-bold',
      file: 'i-ph-file-bold',
      folder: 'i-ph-folder-bold',
      folderOpen: 'i-ph-folder-open-bold',
      hash: 'i-ph-hash-bold',
      info: 'i-ph-info-bold',
      light: 'i-ph-sun-bold',
      loading: 'i-ph-circle-notch-bold',
      menu: 'i-ph-list-bold',
      minus: 'i-ph-minus-bold',
      panelClose: 'i-ph-sidebar-simple-bold',
      panelOpen: 'i-ph-sidebar-simple-bold',
      plus: 'i-ph-plus-bold',
      reload: 'i-ph-arrow-counter-clockwise-bold',
      search: 'i-ph-magnifying-glass-bold',
      stop: 'i-ph-square-bold',
      success: 'i-ph-check-circle-bold',
      system: 'i-ph-monitor-bold',
      tip: 'i-ph-lightbulb-bold',
      upload: 'i-ph-upload-simple-bold',
      warning: 'i-ph-warning-bold',
    },
    // Checked boxes stay neutral too: a selection is state, not an action
    checkbox: { defaultVariants: { color: 'neutral' } },
    // Text fields focus with a neutral ring: the brand hue is kept for actions, not for focus
    input: { defaultVariants: { color: 'neutral' } },
    inputMenu: { defaultVariants: { color: 'neutral' } },
    inputNumber: { defaultVariants: { color: 'neutral' } },
    inputTags: { defaultVariants: { color: 'neutral' } },
    select: { defaultVariants: { color: 'neutral' } },
    selectMenu: { defaultVariants: { color: 'neutral' } },
    textarea: { defaultVariants: { color: 'neutral' } },
    breadcrumb: {
      variants: {
        // The current page stays neutral: weight and contrast mark it, not the brand hue
        active: {
          true: { link: 'text-highlighted font-semibold' },
        },
      },
    },
    fieldGroup: {
      // Joined buttons share their edges: a press scale would pull one away from its neighbour
      base: 'relative *:active:scale-100!',
    },
    button: {
      slots: {
        // Press feedback: a subtle scale confirms the click landed. Tailwind v4 sets the `scale`
        // property (not `transform`), so that is the one to transition or the press snaps
        base: 'transition-[color,background-color,box-shadow,scale] duration-150 ease-out not-disabled:not-aria-disabled:active:scale-[0.97] motion-reduce:active:scale-100',
      },
      compoundVariants: [
        {
          // On dark surfaces the primary hue is lightened (indigo-400) so text and icons read,
          // but a filled button then carries dark-on-light text at a weak ~4:1. Keep the fill
          // deep instead: white on indigo-600 measures 6.3:1, and a faint inner edge keeps the
          // shape readable against the page.
          color: 'primary',
          variant: 'solid',
          class: 'dark:bg-indigo-600 dark:text-white dark:ring-1 dark:ring-inset dark:ring-white/15 dark:hover:bg-indigo-500 dark:active:bg-indigo-500 dark:disabled:bg-indigo-600 dark:aria-disabled:bg-indigo-600',
        },
      ],
    },
  },
})
