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
    },
  },
})
