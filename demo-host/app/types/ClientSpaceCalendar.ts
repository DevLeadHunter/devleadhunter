import type { AiAssistantClientCalendar, AiAssistantClientCalendarUpdate } from '~/types/AiAssistantClientSpace'

/** Props of the client-space agenda section. */
export type ClientSpaceCalendarProps = {
  calendar: AiAssistantClientCalendar
  assistantName: string
  isBusy: boolean
  errorMessage: string | null
  hasSaved: boolean
}

/** Events of the ClientSpaceCalendar component. */
export type ClientSpaceCalendarEmits = {
  connect: []
  save: [update: AiAssistantClientCalendarUpdate]
  disconnect: []
}
