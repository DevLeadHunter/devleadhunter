/** ``order`` = candidate placement (hero/about/gallery), owned by the parent; ``pool`` = every usable photo. */
export type ImageSlotsProps = {
  pool: string[]
  order: string[]
  isHeadingHidden?: boolean
}

export type ImageSlotsEmits = {
  'update:order': [order: string[]]
}
