import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue'
import type { LoginCredentials, Prospect, SignupPayload, User } from '~/types'
import type {
  ScrapingJobHydrationPayload,
  ScrapingJobProgressState,
  ScrapingJobStreamHandlers,
} from '~/composables/useScrapingJobStream'

export type UseAuthReturn = {
  login: (credentials: LoginCredentials) => Promise<void>
  signup: (payload: SignupPayload) => Promise<void>
  logout: () => void
  isAuthenticated: ComputedRef<boolean>
  isLoading: ComputedRef<boolean>
  user: ComputedRef<User | null>
}

export type UseAutomationCompletionNotifierReturn = {
  start: () => void
  stop: () => void
}

export type UseCopyToClipboardReturn = {
  copy: (text: string) => Promise<void>
  copied: Ref<boolean>
}

export type UseDashboardScrollReturn = {
  scrollToTop: (behavior?: ScrollBehavior) => void
  scrollToBottom: (behavior?: ScrollBehavior) => void
}

export type UseDesktopRuntimeReturn = {
  isDesktopApp: ComputedRef<boolean>
  isLocalDev: boolean
  isDesktopDev: ComputedRef<boolean>
  isProdDesktop: ComputedRef<boolean>
  syncDevDatabaseFromProd: () => Promise<string>
}

export type UseLazyPreviewReturn = {
  shouldRenderPreview: Ref<boolean>
  markPreviewLoaded: () => void
}

export type UseOpenExternalUrlReturn = {
  openExternalUrl: (url: string) => Promise<void>
}

export type UseProfilePhotoReturn = {
  hasProfilePhoto: Ref<boolean>
  profilePhotoObjectUrl: Ref<string | null>
  ensureProfilePhotoLoaded: () => Promise<void>
  refreshProfilePhoto: () => Promise<void>
}

export type UseScrapingJobStreamReturn = {
  logs: Ref<string[]>
  prospects: Ref<Prospect[]>
  progress: Ref<ScrapingJobProgressState>
  skippedDuplicates: Ref<number>
  isConnected: Ref<boolean>
  connect: (jobId: string, token: string, streamHandlers?: ScrapingJobStreamHandlers) => void
  disconnect: () => void
  hydrateFromJob: (job: ScrapingJobHydrationPayload) => void
  reset: () => void
}

export type UseToastReturn = {
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  warning: (message: string) => void
}

/** Options of the horizontal-swipe gesture composable (`useHorizontalSwipe`). */
export type HorizontalSwipeOptions = {
  /** Invoked on a left-to-right swipe (finger travels right). */
  onSwipeRight?: () => void
  /** Invoked on a right-to-left swipe (finger travels left). */
  onSwipeLeft?: () => void
  /** The gesture only fires while this resolves truthy (default: always enabled). */
  enabled?: MaybeRefOrGetter<boolean>
  /** Minimum horizontal travel in pixels before a drag counts as a swipe (default 60). */
  threshold?: number
  /** When set, the swipe must start within this many pixels of the left edge. */
  edgeStartPx?: number
  /** CSS selector whose elements swallow the gesture (default: form fields + [data-swipe-ignore]). */
  ignoreSelector?: string
}

export type UseHorizontalSwipeReturn = {
  isSwiping: Ref<boolean>
}

export type DragToReorderAxis = 'vertical' | 'grid'

export type DragToReorderGhostFrame = 'card' | 'none'

/** The container must be the offsetParent of its `data-reorder-key` items (`relative`, or the `<table>` for rows). */
export type DragToReorderOptions<T> = {
  axis: DragToReorderAxis
  getContainer: () => HTMLElement | null
  getOrder: () => T[]
  keyOf: (item: T) => string
  setDraftOrder: (order: T[] | null) => void
  setDraggedKey: (key: string | null) => void
  onCommit: (order: T[]) => void
  onCancel?: () => void
  liftScale?: number
  ghostFrame?: DragToReorderGhostFrame
  morphGhostToSlot?: (ghostCard: HTMLElement, slotElement: HTMLElement, durationMs: number, easing: string) => void
}

export type DragToReorderSession<T> = {
  item: T
  key: string
  pointerId: number
  startClientX: number
  startClientY: number
  lastClientX: number
  lastClientY: number
  grabOffsetX: number
  grabOffsetY: number
  itemLeft: number
  itemWidth: number
  ghost: HTMLElement | null
  ghostInnerLeft: number
  ghostInnerTop: number
  isActive: boolean
  autoscrollFrame: number
  scrollParent: HTMLElement | null
}

export type DragToReorderLanding = {
  finish: () => void
}

export type UseDragToReorderReturn<T> = {
  onGripPointerDown: (event: PointerEvent, item: T) => void
  cancelDrag: () => Promise<void>
}
