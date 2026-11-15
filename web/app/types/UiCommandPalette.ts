/** One actionable row of the palette. */
export type CommandPaletteAction = {
  id: string
  label: string
  icon: string
  meta?: string
  keywords?: string
  requiredPagePath?: string
  run: () => void
  flatIndex: number
}

export type CommandPalettePage = {
  to: string
  label: string
  icon: string
}

/** One displayed group of palette rows. */
export type CommandPaletteGroup = {
  key: string
  heading: string
  items: CommandPaletteAction[]
}
