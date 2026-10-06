import type { ComponentPublicInstance, ComputedRef, MaybeRefOrGetter, Ref, StyleValue } from 'vue'
import type { LoginCredentials, SignupPayload, User } from '~/types'
import type { AtelierSheetSize, AtelierTool } from '~/types/AtelierToolSheet'
import type { ProspectSearchCandidate } from '~/types/ProspectSearch'

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
  copy: (text: string) => Promise<boolean>
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

export type ToastAction = {
  label: string
  onSelect: () => void
}

export type ToastCallOptions = {
  action?: ToastAction
  duration?: number
}

export type UseToastReturn = {
  success: (message: string, options?: ToastCallOptions) => void
  error: (message: string, options?: ToastCallOptions) => void
  info: (message: string, options?: ToastCallOptions) => void
  warning: (message: string, options?: ToastCallOptions) => void
}

export type UseProspectSearchDecisionsReturn = {
  acceptLead: (candidate: ProspectSearchCandidate) => Promise<boolean>
  rejectLead: (candidate: ProspectSearchCandidate) => Promise<boolean>
  acceptLeads: (candidates: ProspectSearchCandidate[]) => Promise<void>
  rejectLeads: (candidates: ProspectSearchCandidate[]) => Promise<void>
  openLead: (candidate: ProspectSearchCandidate, browsedCandidates?: ProspectSearchCandidate[]) => void
  showPendingLeads: () => Promise<void>
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

export type VideoGenerationCheckPace = {
  untilMinutes: number
  everySeconds: number
}

export type UseVideoGenerationChecksReturn = {
  isTakingLongerThanExpected: Ref<boolean>
  startChecks: () => void
  stopChecks: () => void
  checkNow: () => Promise<void>
}

export type PullToRefreshOptions = {
  onRefresh: () => void
  canStart: () => boolean
}

export type UsePullToRefreshReturn = {
  pullDistance: Ref<number>
  pullProgress: ComputedRef<number>
  isPulling: Ref<boolean>
  isRefreshing: Ref<boolean>
  hasReachedRefreshThreshold: ComputedRef<boolean>
}

/** What an atelier page gets from `useAtelierToolSheet`: the open tool, the sheet and the handlers of its handle. */
export type UseAtelierToolSheetReturn<TKey extends string> = {
  activeTool: Ref<TKey | null>
  sheetSize: Ref<AtelierSheetSize>
  workAreaElement: Ref<HTMLElement | null>
  sheetElement: Ref<HTMLElement | null>
  isToolSheetOpen: ComputedRef<boolean>
  activeToolMeta: ComputedRef<AtelierTool<TKey> | null>
  activeToolHint: ComputedRef<string>
  sheetStyle: ComputedRef<StyleValue>
  toggleTool: (key: TKey) => void
  closeActiveTool: () => void
  registerToolButton: (key: TKey, element: Element | ComponentPublicInstance | null) => void
  startSheetDrag: (event: PointerEvent) => void
  followSheetDrag: (event: PointerEvent) => void
  endSheetDrag: (event: PointerEvent) => void
  cancelSheetDrag: () => void
  toggleSheetSize: () => void
}
