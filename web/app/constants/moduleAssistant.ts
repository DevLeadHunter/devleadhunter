import type { ModuleAssistantTone } from '~/types/ModuleAssistant'

export const MODULE_ASSISTANT_LABEL: string = 'Assistant'

export const MODULE_ASSISTANT_ICON: string = 'i-lucide-message-circle'

export const MODULE_ASSISTANT_QUESTION_MAXIMUM_LENGTH: number = 500

/** The colours of a suggestion's icon tile. */
export const MODULE_ASSISTANT_TONE_CLASSES: Record<ModuleAssistantTone, string> = {
  blue: 'bg-[var(--app-blue-soft)] text-[var(--app-blue)]',
  violet: 'bg-[var(--app-violet-soft)] text-[var(--app-violet)]',
  green: 'bg-[var(--app-green-soft)] text-[var(--app-green)]',
  amber: 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]',
  red: 'bg-[var(--app-red-soft)] text-[var(--app-red)]',
}
