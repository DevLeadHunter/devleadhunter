import type { UseScrollReturn } from '@vueuse/core'
import type { ComputedRef, Ref } from 'vue'
import type { TabRowHiddenSides } from '~/types/Composables'
import { useResizeObserver, useScroll } from '@vueuse/core'
import { computed } from 'vue'

const EDGE_FADE_CLASSES: Record<TabRowHiddenSides, string> = {
  none: '',
  left: '[mask-image:linear-gradient(to_right,transparent,#000_2.5rem)]',
  right: '[mask-image:linear-gradient(to_right,#000_calc(100%-2.5rem),transparent)]',
  both: '[mask-image:linear-gradient(to_right,transparent,#000_2.5rem,#000_calc(100%-2.5rem),transparent)]',
}

/**
 * Fade the edges of a sideways-scrolling row of tabs where tabs are still hidden.
 * @param tabRowElement - The row of tabs.
 * @returns The class to put on the row.
 */
export function useTabRowEdgeFade(tabRowElement: Ref<HTMLElement | null>): ComputedRef<string> {
  const { arrivedState, measure }: UseScrollReturn = useScroll(tabRowElement)

  useResizeObserver(tabRowElement, measure)

  const hiddenSides: ComputedRef<TabRowHiddenSides> = computed((): TabRowHiddenSides => {
    if (!arrivedState.left && !arrivedState.right) {
      return 'both'
    }
    if (!arrivedState.left) {
      return 'left'
    }
    if (!arrivedState.right) {
      return 'right'
    }
    return 'none'
  })

  return computed((): string => EDGE_FADE_CLASSES[hiddenSides.value])
}
