import type { Ref } from 'vue'
import type { UseLazyPreviewReturn } from '~/types/Composables'
import { onMounted, onUnmounted, ref } from 'vue'

/**
 * Loads previews (demo-site iframes) under control: each preview mounts only
 * once its card actually enters the viewport, and a GLOBAL cap bounds how many
 * iframes load at the same time.
 *
 * Without this guard a grid of 40 sites would start dozens of live renders at
 * once — each iframe is a full app (JS, fonts, requests) — and bog the page down.
 * `loading="lazy"` alone does not bound concurrency on an iframe: it only defers
 * the ones far off-screen.
 *
 * @module composables/useLazyPreview
 */

/** Maximum previews loading at the same time, across every card. */
const MAX_CONCURRENT_PREVIEWS: number = 4

/** Viewport margin that preloads a preview just before it becomes visible. */
const PREVIEW_ROOT_MARGIN: string = '400px'

/** Safety net: release a slot even if an iframe's `load` never fires (blocked network). */
const PREVIEW_LOAD_TIMEOUT_MS: number = 15000

/** Previews currently loading. */
let activePreviewCount: number = 0

/** Cards waiting for a free slot, in the order they entered the screen. */
const previewWaiters: Array<() => void> = []

/** A reserved loading slot: `ready` resolves once it is granted. */
type PreviewSlot = {
  ready: Promise<void>
  release: () => void
}

/** Hand an active slot to the next waiting card, or decrement the counter. */
function releaseActiveSlot(): void {
  const nextWaiter: (() => void) | undefined = previewWaiters.shift()
  if (nextWaiter) {
    // Hand the slot straight to the next waiter: the counter stays constant.
    nextWaiter()
    return
  }
  activePreviewCount = Math.max(0, activePreviewCount - 1)
}

/**
 * Drop a still-waiting ticket (card unmounted before its turn).
 * @param waiter - The resolver queued by reservePreviewSlot.
 */
function cancelWaiter(waiter: () => void): void {
  const index: number = previewWaiters.indexOf(waiter)
  if (index !== -1) previewWaiters.splice(index, 1)
}

/**
 * Reserve a preview loading slot: granted right away while the cap is free,
 * otherwise queued until a slot frees up.
 * @returns The reserved slot — call release() once the preview is loaded (or the
 * card unmounted) to hand the place to the next one.
 */
function reservePreviewSlot(): PreviewSlot {
  let isReleased: boolean = false

  // Free slot: granted immediately.
  if (activePreviewCount < MAX_CONCURRENT_PREVIEWS) {
    activePreviewCount += 1
    return {
      ready: Promise.resolve(),
      release: (): void => {
        if (isReleased) return
        isReleased = true
        releaseActiveSlot()
      },
    }
  }

  // Cap reached: take a ticket in the queue.
  let isGranted: boolean = false
  let onGranted: () => void = (): void => {}
  const ready: Promise<void> = new Promise<void>((resolve: () => void): void => {
    onGranted = (): void => {
      isGranted = true
      resolve()
    }
    previewWaiters.push(onGranted)
  })
  return {
    ready,
    release: (): void => {
      if (isReleased) return
      isReleased = true
      if (isGranted) releaseActiveSlot()
      else cancelWaiter(onGranted)
    },
  }
}

/**
 * Mount a card's preview when it enters the viewport, under a global cap on
 * simultaneous loads.
 * @param previewTarget - The observed container element (the card's preview area).
 * @param isPreviewEnabled - Returns true when the card actually has a preview to
 * load; a card without a preview reserves no slot.
 * @returns The controls to wire onto the card's iframe.
 */
export function useLazyPreview(
  previewTarget: Readonly<Ref<HTMLElement | null>>,
  isPreviewEnabled: () => boolean,
): UseLazyPreviewReturn {
  const shouldRenderPreview: Ref<boolean> = ref(false)
  let observer: IntersectionObserver | null = null
  let slot: PreviewSlot | null = null
  let loadTimeout: ReturnType<typeof setTimeout> | null = null

  /** Stop observing the viewport (one-shot: the preview mounts only once). */
  const stopObserving: () => void = (): void => {
    observer?.disconnect()
    observer = null
  }

  /** The preview is painted (or given up): hand its slot to the next one. */
  const markPreviewLoaded: () => void = (): void => {
    if (loadTimeout !== null) {
      clearTimeout(loadTimeout)
      loadTimeout = null
    }
    slot?.release()
    slot = null
  }

  /** The card enters the viewport: reserve a slot, then mount the iframe. */
  const enterViewport: () => Promise<void> = async (): Promise<void> => {
    stopObserving()
    const reserved: PreviewSlot = reservePreviewSlot()
    slot = reserved
    await reserved.ready
    // Unmounted (or released) while waiting: mount nothing.
    if (slot !== reserved) return
    shouldRenderPreview.value = true
    loadTimeout = setTimeout(markPreviewLoaded, PREVIEW_LOAD_TIMEOUT_MS)
  }

  onMounted((): void => {
    if (!import.meta.client || !isPreviewEnabled()) return
    const target: HTMLElement | null = previewTarget.value
    if (!target) return
    if (typeof IntersectionObserver === 'undefined') {
      // Browser without IntersectionObserver: load without deferring.
      void enterViewport()
      return
    }
    observer = new IntersectionObserver(
      (entries: IntersectionObserverEntry[]): void => {
        if (entries.some((entry: IntersectionObserverEntry): boolean => entry.isIntersecting)) {
          void enterViewport()
        }
      },
      { rootMargin: PREVIEW_ROOT_MARGIN },
    )
    observer.observe(target)
  })

  onUnmounted((): void => {
    stopObserving()
    if (loadTimeout !== null) clearTimeout(loadTimeout)
    slot?.release()
    slot = null
  })

  return { shouldRenderPreview, markPreviewLoaded }
}
