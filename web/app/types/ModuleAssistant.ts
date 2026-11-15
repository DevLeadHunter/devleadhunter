import type { UiBarChartBar } from '~/types/UiBarChart'

export type ModuleAssistantTone = 'blue' | 'violet' | 'green' | 'amber' | 'red'

/** A question the owner sends with one touch. */
export type ModuleAssistantSuggestion = {
  label: string
  tone: ModuleAssistantTone
  icon: string
}

/** What the assistant shows before the first question. */
export type ModuleAssistantHome = {
  lead: string
  suggestions: ModuleAssistantSuggestion[]
}

export type ModuleAssistantChart = {
  title: string
  bars: UiBarChartBar[]
}

/** One thing to look at first, such as a reply received; `text` quotes it when there is something to quote. */
export type ModuleAssistantHighlight = {
  title: string
  badge: string
  meta: string
  text: string | null
  link_label: string
  link_to: string
}

/** An answer of the assistant; `cards` are the module's own records, drawn by the module. */
export type ModuleAssistantAnswer<AnswerCard> = {
  text: string
  chart: ModuleAssistantChart | null
  highlight: ModuleAssistantHighlight | null
  next_questions: string[]
  cards: AnswerCard[]
}

/** A question of the conversation and its answer, null while it is awaited. */
export type ModuleAssistantExchange<AnswerCard> = {
  id: number
  question: string
  answer: ModuleAssistantAnswer<AnswerCard> | null
  hasFailed: boolean
}
