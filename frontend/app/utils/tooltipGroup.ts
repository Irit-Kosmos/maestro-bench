import type { InjectionKey } from 'vue'

/** Set inside a UITooltipGroup: controls describe themselves with data-tooltip instead of their own UTooltip */
export const tooltipGroupKey: InjectionKey<boolean> = Symbol('tooltipGroup')
