import type {
  DemoSitePhotoLabel,
  DemoSiteServiceCardsAnalysis,
  DemoSiteServiceCardsConfig,
} from '~/services/demoSiteService'

/** One editor row; ``key`` is the row identity for drag-and-drop (never sent to the API), ``reason`` the AI's justification. */
export type ServiceCardDraft = {
  key: string
  title: string
  description: string
  image: string
  reason: string
}

/** ``cards`` = the candidate rows, owned by the parent (controlled); ``pool`` = every usable photo with its label. */
export type ServiceCardsEditorProps = {
  cards: ServiceCardDraft[]
  pool: DemoSitePhotoLabel[]
  config: DemoSiteServiceCardsConfig
  aiAvailable?: boolean
  suggesting?: boolean
  suggestionError?: string | null
  analysis?: DemoSiteServiceCardsAnalysis | null
  overrideActive?: boolean
  overrideSource?: string | null
  labelsPending?: number
}

export type ServiceCardsEditorEmits = {
  'update:cards': [cards: ServiceCardDraft[]]
  suggest: []
  reset: []
}
