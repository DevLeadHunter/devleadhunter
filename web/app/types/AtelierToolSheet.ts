import type { ComponentPublicInstance, ComputedRef, Ref, StyleValue } from 'vue'

/** One tool of an atelier bar and the title of its sheet; `coarsePointerHint` replaces `hint` on a touch screen. */
export type AtelierTool<TKey extends string> = {
  key: TKey
  label: string
  icon: string
  title: string
  hint: string
  coarsePointerHint?: string
}

/** How high the sheet stands: the setting height, with the preview above it, or nearly the whole area. */
export type AtelierSheetSize = 'setting' | 'expanded'

/** A drag of the sheet's handle, followed from the finger or the pointer that started it. */
export type AtelierSheetDrag = {
  pointerId: number
  startY: number
  startHeight: number
  areaHeight: number
  hasMoved: boolean
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
