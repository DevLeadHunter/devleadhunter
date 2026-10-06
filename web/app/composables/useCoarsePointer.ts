import type { Ref } from 'vue'
import { onBeforeUnmount, onMounted, ref } from 'vue'

const COARSE_POINTER_QUERY: string = '(pointer: coarse)'

/**
 * Whether the device is driven by a finger rather than a mouse: true on an iPad (keyboard or not) and a phone,
 * false on a computer and in the Windows app. Follows the device when its main pointer changes; always false on the
 * server and until the component is mounted.
 * @returns A reactive flag, true while the main pointer is coarse.
 */
export function useCoarsePointer(): Ref<boolean> {
  const isCoarsePointer: Ref<boolean> = ref(false)
  let mediaQuery: MediaQueryList | null = null

  /**
   * Mirror the media query into the flag.
   * @param event - The query's new state.
   */
  function onPointerQueryChange(event: MediaQueryListEvent): void {
    isCoarsePointer.value = event.matches
  }

  onMounted((): void => {
    mediaQuery = window.matchMedia(COARSE_POINTER_QUERY)
    isCoarsePointer.value = mediaQuery.matches
    mediaQuery.addEventListener('change', onPointerQueryChange)
  })

  onBeforeUnmount((): void => {
    mediaQuery?.removeEventListener('change', onPointerQueryChange)
  })

  return isCoarsePointer
}
