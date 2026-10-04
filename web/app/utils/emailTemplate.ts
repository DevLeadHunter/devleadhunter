import type { EmailTemplate, EmailTemplateCategory, EmailTemplateLayout } from '~/types'

/** Sequence steps a template can belong to, in the order the tabs display them. */
export const EMAIL_TEMPLATE_CATEGORIES: EmailTemplateCategory[] = ['first_email', 'follow_up']

/** Human label of each sequence step. */
export const EMAIL_TEMPLATE_CATEGORY_LABELS: Record<EmailTemplateCategory, string> = {
  first_email: 'Premier email',
  follow_up: 'Relance',
}

export const EMAIL_TEMPLATE_LAYOUTS: EmailTemplateLayout[] = ['plain', 'card', 'card_table']

/** Layout a new template starts with: the card with the offer table, like the whole library. */
export const DEFAULT_EMAIL_TEMPLATE_LAYOUT: EmailTemplateLayout = 'card_table'

export const EMAIL_TEMPLATE_LAYOUT_LABELS: Record<EmailTemplateLayout, string> = {
  plain: 'Simple (texte seul)',
  card: 'Carte',
  card_table: 'Carte avec tableau',
}

export const EMAIL_TEMPLATE_LAYOUT_DESCRIPTIONS: Record<EmailTemplateLayout, string> = {
  plain: 'Le texte part tel quel, suivi de la signature.',
  card: 'Le texte part dans une carte blanche, avec un bouton sous le lien, le prix et la date en gras.',
  card_table:
    'Comme la carte, et les phrases du prix, de la date et de la réponse deviennent un tableau. L’onglet Aperçu montre le résultat.',
}

/**
 * Whether a template is one of the recommended picks, pinned at the top of its tab.
 * @param template - Template to test.
 * @returns True when the template carries a pinning weight.
 */
export function isTemplateRecommended(template: EmailTemplate): boolean {
  return (template.sort_order ?? 0) > 0
}

/**
 * Template name without its leading « ★ », which the seeded names embed as text.
 * The app renders that star itself, in the accent colour, so keeping it in the
 * string would show it twice.
 * @param name - Raw template name.
 * @returns The name stripped of a leading star and its spacing.
 */
export function templateNameWithoutStar(name: string): string {
  return name.replace(/^\s*★\s*/, '')
}
