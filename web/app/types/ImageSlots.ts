/** ``order`` = candidate placement (hero/about/gallery), owned by the parent; ``pool`` = every usable photo. */
export type ImageSlotsProps = {
  pool: string[]
  order: string[]
  isHeadingHidden?: boolean
}

export type ImageSlotsEmits = {
  'update:order': [order: string[]]
}

/** A finger resting on a grid tile, waiting to hold long enough to lift the photo. */
export type ImageGridLongPress = {
  url: string
  tile: HTMLElement
  pointerId: number
  startClientX: number
  startClientY: number
  lastClientX: number
  lastClientY: number
  timer: ReturnType<typeof setTimeout>
}
