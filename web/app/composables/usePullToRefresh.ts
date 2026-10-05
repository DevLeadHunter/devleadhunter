import type { ComputedRef, Ref } from 'vue'
import type { PullToRefreshOptions, UsePullToRefreshReturn } from '~/types/Composables'
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { isStandalonePwa } from '~/utils/webPush'

const REFRESH_THRESHOLD_PX: number = 72
const MAXIMUM_PULL_DISTANCE_PX: number = 110
const FINGER_TO_INDICATOR_RATIO: number = 0.5
const GESTURE_DIRECTION_SLOP_PX: number = 6

// Dialogs, maps, drag grips (`touch-none`) and form fields follow the finger themselves, and a reload
// would lose what is being typed: a pull starting there is not a refresh.
const PULL_TO_REFRESH_IGNORED_SELECTOR: string = [
  '[role="dialog"]',
  '[aria-modal="true"]',
  '[data-no-pull-to-refresh]',
  '.touch-none',
  '.maplibregl-map',
  'input',
  'textarea',
  'select',
  '[contenteditable="true"]',
].join(', ')

/**
 * Refresh the page when it is pulled down from its top, in the installed app only: Safari offers no
 * pull-to-refresh nor reload button once the app runs from the home screen.
 * @param options - What a pull past the threshold does, and when a pull may start.
 * @returns How far the page is pulled and the gesture state, for the indicator.
 */
export function usePullToRefresh(options: PullToRefreshOptions): UsePullToRefreshReturn {
  const pullDistance: Ref<number> = ref(0)
  const isPulling: Ref<boolean> = ref(false)
  const isRefreshing: Ref<boolean> = ref(false)

  const pullProgress: ComputedRef<number> = computed((): number =>
    Math.min(1, pullDistance.value / REFRESH_THRESHOLD_PX),
  )
  const hasReachedRefreshThreshold: ComputedRef<boolean> = computed((): boolean => pullProgress.value >= 1)

  let gestureStartX: number = 0
  let gestureStartY: number = 0
  let isGestureFollowed: boolean = false

  /**
   * Whether the finger lands on content already scrolled down: the gesture then scrolls it back up.
   * @param touchedElement - Element under the finger.
   * @returns True when one of its containers is not at its top.
   */
  function isInsideScrolledContent(touchedElement: Element): boolean {
    for (let element: Element | null = touchedElement; element; element = element.parentElement) {
      if (element.scrollTop > 0) return true
    }
    return false
  }

  /**
   * Start following a finger laid at the top of the page, outside dialogs and maps.
   * @param event - The finger touching the screen.
   */
  function onTouchStart(event: TouchEvent): void {
    isGestureFollowed = false
    const touch: Touch | null = event.touches.item(0)
    if (isRefreshing.value || event.touches.length !== 1 || !touch || !isStandalonePwa() || !options.canStart()) {
      return
    }
    if (!(event.target instanceof Element) || event.target.closest(PULL_TO_REFRESH_IGNORED_SELECTOR)) return
    if (isInsideScrolledContent(event.target)) return
    gestureStartX = touch.clientX
    gestureStartY = touch.clientY
    isGestureFollowed = true
  }

  /**
   * Bring the indicator down with the finger, once the gesture is known to go down rather than sideways.
   * @param event - The finger moving.
   */
  function onTouchMove(event: TouchEvent): void {
    const touch: Touch | null = event.touches.item(0)
    if (!isGestureFollowed || !touch) return
    const horizontalDistance: number = touch.clientX - gestureStartX
    const verticalDistance: number = touch.clientY - gestureStartY
    if (!isPulling.value) {
      const isStillUndecided: boolean =
        Math.abs(horizontalDistance) < GESTURE_DIRECTION_SLOP_PX &&
        Math.abs(verticalDistance) < GESTURE_DIRECTION_SLOP_PX
      if (isStillUndecided) return
      if (verticalDistance <= 0 || Math.abs(horizontalDistance) > verticalDistance) {
        isGestureFollowed = false
        return
      }
      isPulling.value = true
    }
    pullDistance.value = Math.min(MAXIMUM_PULL_DISTANCE_PX, Math.max(0, verticalDistance * FINGER_TO_INDICATOR_RATIO))
    // Without it, iOS bounces the page under the indicator.
    if (event.cancelable) event.preventDefault()
  }

  /** Refresh when the finger is lifted past the threshold, otherwise put the indicator back. */
  function onTouchEnd(): void {
    isGestureFollowed = false
    if (!isPulling.value) return
    isPulling.value = false
    if (hasReachedRefreshThreshold.value) {
      isRefreshing.value = true
      pullDistance.value = REFRESH_THRESHOLD_PX
      options.onRefresh()
      return
    }
    pullDistance.value = 0
  }

  onMounted((): void => {
    if (navigator.maxTouchPoints === 0) return
    document.addEventListener('touchstart', onTouchStart, { passive: true })
    document.addEventListener('touchmove', onTouchMove, { passive: false })
    document.addEventListener('touchend', onTouchEnd, { passive: true })
    document.addEventListener('touchcancel', onTouchEnd, { passive: true })
  })

  onBeforeUnmount((): void => {
    document.removeEventListener('touchstart', onTouchStart)
    document.removeEventListener('touchmove', onTouchMove)
    document.removeEventListener('touchend', onTouchEnd)
    document.removeEventListener('touchcancel', onTouchEnd)
  })

  return { pullDistance, pullProgress, isPulling, isRefreshing, hasReachedRefreshThreshold }
}
