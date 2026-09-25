import type { AiAssistantSummary } from '~/types/AiAssistant'

/** Props of the drawer editing an assistant's identity, alerts and model constraints. */
export type UiAssistantSettingsDrawerProps = {
  open: boolean
  assistant: AiAssistantSummary | null
  showBack: boolean
}

/** Events the settings drawer emits; `saved` carries the assistant as the API returned it. */
export type UiAssistantSettingsDrawerEmits = {
  close: []
  back: []
  saved: [assistant: AiAssistantSummary]
}
