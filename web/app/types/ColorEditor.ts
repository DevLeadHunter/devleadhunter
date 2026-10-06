import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

/** Props of the shared site colour editor (template picker of the creation tunnel + colour sheet of the atelier). */
export type ColorEditorProps = {
  /** Template whose colour roles drive the swatches. Null renders nothing (no template selected). */
  template: DemoSiteTemplate | null
  theme: DemoSiteTheme
  /** Action colour = the prospect logo (true) or the template default (false). Null hides the Logo/Template picker (wizard). */
  useBrandColor?: boolean | null
  /** The colour extracted from the prospect logo, for the « Celle du logo » card. Null = no usable logo colour. */
  brandColor?: string | null
}

export type ColorEditorEmits = {
  'update:theme': [value: DemoSiteTheme]
  'update:useBrandColor': [value: boolean]
}

/** One editable colour swatch, resolved from the template's canonical roles. */
export type EditableColor = {
  key: keyof DemoSiteTheme
  label: string
  isAction: boolean
}
