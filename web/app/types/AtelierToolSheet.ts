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
