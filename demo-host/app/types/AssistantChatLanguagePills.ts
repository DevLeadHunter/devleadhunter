import type { AssistantWidgetLang } from '~/types/AiAssistant'

export type AssistantChatLanguagePillsProps = {
  languages: AssistantWidgetLang[]
  modelValue: AssistantWidgetLang
}

export type AssistantChatLanguagePillsEmits = {
  'update:modelValue': [code: AssistantWidgetLang]
}
