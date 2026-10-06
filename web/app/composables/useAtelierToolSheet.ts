import type { ComponentPublicInstance, ComputedRef, Ref, StyleValue } from 'vue'
import type {
  AtelierSheetDrag,
  AtelierSheetSize,
  AtelierTool,
  UseAtelierToolSheetReturn,
} from '~/types/AtelierToolSheet'
import { useEventListener } from '@vueuse/core'
import { computed, nextTick, ref } from 'vue'

/** At its setting height the sheet takes at most this share of the work area: the preview stays visible above it. */
const SHEET_SETTING_MAX_HEIGHT_RATIO: number = 0.44

/** The sheet's expanded height, as a share of the work area. */
const SHEET_EXPANDED_HEIGHT_RATIO: number = 0.8

/** A move of the handle shorter than this is a tap, not a drag. */
const SHEET_DRAG_START_DISTANCE_PX: number = 6

/** Released below this share of its setting height, the sheet closes. */
const SHEET_CLOSE_HEIGHT_RATIO: number = 0.5

/**
 * The tool bar and the sheet of an atelier page: one tool open at a time, in a sheet under the preview that the
 * finger drags between two heights; the keys in `pageToolKeys` open a full page instead of a sheet.
 * @param tools - The tools of the bar, in order.
 * @param pageToolKeys - The tools that take the whole area rather than a sheet.
 * @param isCoarsePointer - Whether the screen is touched, which picks the finger hints.
 * @returns The open tool, the sheet's size and style, and the handlers of the bar and the handle.
 */
export function useAtelierToolSheet<TKey extends string>(
  tools: AtelierTool<TKey>[],
  pageToolKeys: TKey[],
  isCoarsePointer: Ref<boolean>,
): UseAtelierToolSheetReturn<TKey> {
  const activeTool: Ref<TKey | null> = ref(null) as Ref<TKey | null>
  const sheetSize: Ref<AtelierSheetSize> = ref('setting')
  /** Height of the sheet while its handle is dragged, in pixels; null when it rests at one of its two heights. */
  const sheetDragHeight: Ref<number | null> = ref(null)
  const workAreaElement: Ref<HTMLElement | null> = ref(null)
  const sheetElement: Ref<HTMLElement | null> = ref(null)
  let sheetDrag: AtelierSheetDrag | null = null
  let shouldIgnoreNextHandleClick: boolean = false
  const toolButtonElements: Map<TKey, HTMLElement> = new Map()

  /** A tool sheet stands under the preview (a page tool takes the whole area instead). */
  const isToolSheetOpen: ComputedRef<boolean> = computed(
    (): boolean => activeTool.value !== null && !pageToolKeys.includes(activeTool.value),
  )

  const activeToolMeta: ComputedRef<AtelierTool<TKey> | null> = computed(
    (): AtelierTool<TKey> | null =>
      tools.find((tool: AtelierTool<TKey>): boolean => tool.key === activeTool.value) ?? null,
  )

  /** The sheet's subtitle: on a touch screen, a tool may explain its finger gestures instead. */
  const activeToolHint: ComputedRef<string> = computed((): string => {
    const tool: AtelierTool<TKey> | null = activeToolMeta.value
    if (!tool) return ''
    return isCoarsePointer.value && tool.coarsePointerHint ? tool.coarsePointerHint : tool.hint
  })

  /** The sheet's height: following the finger during a drag, otherwise its setting or its expanded height. */
  const sheetStyle: ComputedRef<StyleValue> = computed((): StyleValue => {
    if (sheetDragHeight.value !== null) return { height: `${sheetDragHeight.value}px` }
    if (sheetSize.value === 'expanded') return { height: `${SHEET_EXPANDED_HEIGHT_RATIO * 100}%` }
    return { maxHeight: `${SHEET_SETTING_MAX_HEIGHT_RATIO * 100}%` }
  })

  /**
   * Close the open sheet (or the page tool) and give the focus back to its tool in the bar.
   */
  function closeActiveTool(): void {
    const closedTool: TKey | null = activeTool.value
    activeTool.value = null
    sheetDragHeight.value = null
    sheetDrag = null
    sheetSize.value = 'setting'
    if (closedTool === null) return
    void nextTick((): void => {
      toolButtonElements.get(closedTool)?.focus({ preventScroll: true })
    })
  }

  /**
   * Open a tool, at the setting height when no sheet was open, or close it when it is the one open.
   * @param key - The tool touched in the bar.
   */
  function toggleTool(key: TKey): void {
    if (activeTool.value === key) {
      closeActiveTool()
      return
    }
    if (activeTool.value === null) sheetSize.value = 'setting'
    sheetDragHeight.value = null
    activeTool.value = key
    if (!pageToolKeys.includes(key)) {
      void nextTick((): void => {
        sheetElement.value?.focus({ preventScroll: true })
      })
    }
  }

  /**
   * Remember a tool's button in the bar, to give it the focus back when its sheet closes.
   * @param key - The tool the button opens.
   * @param element - The rendered button, or null when it leaves the bar.
   */
  function registerToolButton(key: TKey, element: Element | ComponentPublicInstance | null): void {
    if (element instanceof HTMLElement) {
      toolButtonElements.set(key, element)
      return
    }
    toolButtonElements.delete(key)
  }

  /**
   * Start following a drag of the sheet's handle.
   * @param event - The finger or the pointer pressed on the handle.
   */
  function startSheetDrag(event: PointerEvent): void {
    shouldIgnoreNextHandleClick = false
    if (!sheetElement.value || !workAreaElement.value) return
    sheetDrag = {
      pointerId: event.pointerId,
      startY: event.clientY,
      startHeight: sheetElement.value.offsetHeight,
      areaHeight: workAreaElement.value.clientHeight,
      hasMoved: false,
    }
    if (event.currentTarget instanceof HTMLElement) event.currentTarget.setPointerCapture(event.pointerId)
  }

  /**
   * Resize the sheet with the finger, between nothing and its expanded height.
   * @param event - The finger or the pointer moving.
   */
  function followSheetDrag(event: PointerEvent): void {
    if (!sheetDrag || event.pointerId !== sheetDrag.pointerId) return
    const raisedDistance: number = sheetDrag.startY - event.clientY
    if (!sheetDrag.hasMoved && Math.abs(raisedDistance) < SHEET_DRAG_START_DISTANCE_PX) return
    sheetDrag.hasMoved = true
    const expandedHeight: number = sheetDrag.areaHeight * SHEET_EXPANDED_HEIGHT_RATIO
    sheetDragHeight.value = Math.min(expandedHeight, Math.max(0, sheetDrag.startHeight + raisedDistance))
  }

  /**
   * Settle the sheet where the drag left it: expanded past the middle of its two heights, closed when pulled
   * well below its setting height, back to its setting height otherwise.
   * @param event - The finger or the pointer lifted.
   */
  function endSheetDrag(event: PointerEvent): void {
    if (!sheetDrag || event.pointerId !== sheetDrag.pointerId) return
    const finishedDrag: AtelierSheetDrag = sheetDrag
    sheetDrag = null
    if (!finishedDrag.hasMoved) return
    shouldIgnoreNextHandleClick = true
    const releasedHeight: number = sheetDragHeight.value ?? finishedDrag.startHeight
    sheetDragHeight.value = null
    const settingHeight: number =
      sheetSize.value === 'setting'
        ? finishedDrag.startHeight
        : finishedDrag.areaHeight * SHEET_SETTING_MAX_HEIGHT_RATIO
    const expandedHeight: number = finishedDrag.areaHeight * SHEET_EXPANDED_HEIGHT_RATIO
    if (releasedHeight < settingHeight * SHEET_CLOSE_HEIGHT_RATIO) {
      closeActiveTool()
      return
    }
    sheetSize.value = releasedHeight > (settingHeight + expandedHeight) / 2 ? 'expanded' : 'setting'
  }

  /**
   * Put the sheet back at its resting height when the system takes the gesture over.
   */
  function cancelSheetDrag(): void {
    sheetDrag = null
    sheetDragHeight.value = null
  }

  /**
   * Switch the sheet between its two heights when its handle is touched (or pressed from the keyboard).
   */
  function toggleSheetSize(): void {
    if (shouldIgnoreNextHandleClick) {
      shouldIgnoreNextHandleClick = false
      return
    }
    sheetSize.value = sheetSize.value === 'expanded' ? 'setting' : 'expanded'
  }

  /**
   * Close the open sheet with Escape, unless something else already handled the key or a dialog above the page
   * takes it for itself.
   * @param event - The key pressed anywhere on the page.
   */
  function onDocumentKeydown(event: KeyboardEvent): void {
    if (event.key !== 'Escape' || event.defaultPrevented || activeTool.value === null) return
    if (document.querySelector('[role="dialog"], [aria-modal="true"]')) return
    closeActiveTool()
  }

  useEventListener(document, 'keydown', onDocumentKeydown)

  return {
    activeTool,
    sheetSize,
    workAreaElement,
    sheetElement,
    isToolSheetOpen,
    activeToolMeta,
    activeToolHint,
    sheetStyle,
    toggleTool,
    closeActiveTool,
    registerToolButton,
    startSheetDrag,
    followSheetDrag,
    endSheetDrag,
    cancelSheetDrag,
    toggleSheetSize,
  }
}
