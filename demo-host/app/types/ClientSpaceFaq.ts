import type { AiAssistantClientFaqEntry, AiAssistantClientUnansweredEntry } from '~/types/AiAssistantClientSpace'

/** Props of the client space's questions card: what visitors asked without an answer, and the answers given. */
export type ClientSpaceFaqProps = {
  assistantName: string
  unanswered: AiAssistantClientUnansweredEntry[]
  faq: AiAssistantClientFaqEntry[]
  isBusy: boolean
  errorMessage: string | null
  /** In the example space: the questions are shown, none can be answered. */
  readOnly: boolean
}

/** Events of the card: an answer to record, a question to drop. */
export type ClientSpaceFaqEmits = {
  answer: [question: string, answer: string]
  dismiss: [index: number]
}
