import type { AiAssistantPersonaGender } from '~/types/AiAssistant'

/**
 * Portraits shipped in `public/avatars/`, by the persona's first name folded to a slug (« léa » → `lea`).
 * A name absent from the list falls back to the gender's default portrait when one is shipped, else to the
 * drawn bust.
 */
export const ASSISTANT_PORTRAIT_SLUGS: string[] = []

/** The default portrait of each gender, when shipped (`public/avatars/default-feminine.webp`…). */
export const ASSISTANT_DEFAULT_PORTRAITS: Record<AiAssistantPersonaGender, boolean> = {
  feminine: false,
  masculine: false,
}
