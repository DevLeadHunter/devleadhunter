import type { ModuleAssistantAnswer, ModuleAssistantHome } from '~/types/ModuleAssistant'

export type UiModuleAssistantChatProps<AnswerCard> = {
  loadHome: () => Promise<ModuleAssistantHome>
  askQuestion: (question: string) => Promise<ModuleAssistantAnswer<AnswerCard>>
}
