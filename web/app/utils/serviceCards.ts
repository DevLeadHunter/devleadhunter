import type { DemoSiteServiceCard, DemoSiteServiceCardSuggestion } from '~/services/demoSiteService'
import type { ServiceCardDraft } from '~/types/ServiceCardsEditor'

/**
 * Conversions between the section cards of the API (food « Nos spécialités ») and the editor rows.
 */
export class ServiceCards {
  /**
   * Stable key for a card row (drag-and-drop and `v-for` identity), independent of its editable fields.
   * @returns A unique key.
   */
  static newKey(): string {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return crypto.randomUUID()
    return `card-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
  }

  /**
   * Editor rows from the cards published (or suggested) by the API.
   * @param cards - Cards from the API (suggestions carry their `reason`).
   * @returns Draft rows with a fresh key each.
   */
  static toDrafts(cards: Array<DemoSiteServiceCard | DemoSiteServiceCardSuggestion>): ServiceCardDraft[] {
    return cards.map(
      (card: DemoSiteServiceCard | DemoSiteServiceCardSuggestion): ServiceCardDraft => ({
        key: ServiceCards.newKey(),
        title: card.title,
        description: card.description ?? '',
        image: card.image ?? '',
        reason: 'reason' in card ? (card.reason ?? '') : '',
      }),
    )
  }

  /**
   * The API payload of the editor rows (trimmed, without editor-only fields).
   * @param drafts - Editor rows.
   * @returns Cards ready for the PATCH / live preview.
   */
  static toPayload(drafts: ServiceCardDraft[]): DemoSiteServiceCard[] {
    return drafts.map(
      (draft: ServiceCardDraft): DemoSiteServiceCard => ({
        title: draft.title.trim(),
        description: draft.description.trim(),
        image: draft.image.trim(),
      }),
    )
  }

  /**
   * Order-sensitive signature of a card list, to detect pending edits against the published cards.
   * @param cards - Cards or editor rows.
   * @returns A string equal for two lists with the same titles, descriptions and photos in the same order.
   */
  static signature(cards: Array<DemoSiteServiceCard | ServiceCardDraft>): string {
    return cards
      .map(
        (card: DemoSiteServiceCard | ServiceCardDraft): string =>
          `${card.title.trim()}${(card.description ?? '').trim()}${(card.image ?? '').trim()}`,
      )
      .join('')
  }
}
