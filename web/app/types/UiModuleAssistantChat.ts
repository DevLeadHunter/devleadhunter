import type { ModuleAssistantAnswer, ModuleAssistantHome, ModuleAssistantPastExchange } from '~/types/ModuleAssistant'

export type UiModuleAssistantChatProps<AnswerCard> = {
  conversationKey: string
  loadHome: () => Promise<ModuleAssistantHome>
  askQuestion: (question: string, history: ModuleAssistantPastExchange[]) => Promise<ModuleAssistantAnswer<AnswerCard>>
}
