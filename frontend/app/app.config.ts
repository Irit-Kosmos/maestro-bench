export default defineAppConfig({
  ui: {
    colors: {
      primary: 'indigo',
      neutral: 'slate',
    },
    button: {
      slots: {
        // Press feedback: a subtle scale confirms the click landed
        base: 'transition-[color,background-color,box-shadow,transform] duration-150 ease-out not-disabled:not-aria-disabled:active:scale-[0.97] motion-reduce:active:scale-100',
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
