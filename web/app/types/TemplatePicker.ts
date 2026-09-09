import type { DemoSiteServiceCard, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

export type TemplatePickerProps = {
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
  recommendedTrade?: string | null
  publishedSiteUrl?: string | null
  /** Bump to force the live preview iframe to reload (the published URL itself doesn't change). */
  reloadNonce?: number
  templatesBelowPreview?: boolean
  /** Action colour = the prospect logo (true) or the template default (false). Null hides the Logo/Template picker (wizard). */
  useBrandColor?: boolean | null
  /** The colour extracted from the prospect logo, for the "Logo" pill. Null = no usable logo colour. */
  brandColor?: string | null
  /** Hide the colour editor (the demo-site page hosts it in its configuration tab instead). */
  showColors?: boolean
  /** Candidate photo placement pushed live into the published-site preview. Null = published placement. */
  previewPhotos?: string[] | null
  /** Candidate colours pushed live into the published-site preview. Null = published palette. */
  previewTheme?: DemoSiteTheme | null
  /** Candidate section cards (food « Nos spécialités ») pushed live into the preview. Null = published cards. */
  previewServices?: DemoSiteServiceCard[] | null
}

export type TemplateThemeColorKey = keyof DemoSiteTheme

export type TemplatePreviewDevice = 'desktop' | 'mobile'

export type TemplatePickerEmits = {
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
  'update:useBrandColor': [value: boolean]
}
