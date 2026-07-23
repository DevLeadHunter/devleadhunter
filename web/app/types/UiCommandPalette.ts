/** One actionable row of the palette. */
export type CommandPaletteAction = {
  id: string
  label: string
  icon: string
  meta?: string
  keywords?: string
  run: () => void
  flatIndex: number
}

/** One displayed group of palette rows. */
export type CommandPaletteGroup = {
  key: string
  heading: string
  items: CommandPaletteAction[]
}
