// No « ? » nor « & »: an address may not smuggle a header (« ?bcc=… ») into the mailto link.
const EMAIL_PATTERN: RegExp = /^[^@\s?&]+@[^@\s?&]+\.[^@\s?&]+$/
const PHONE_PATTERN: RegExp = /^\+?[\d\s.()-]{6,}$/

/**
 * Tap-to-call, tap-to-mail and map links for the contacts on the public pages.
 */
export class ContactLinkUtils {
  /**
   * A `tel:` or `mailto:` link for a visitor's contact, when it reads as one.
   * @param contact - The contact the visitor left.
   * @returns The href, or null for anything else.
   */
  static href(contact: string): string | null {
    const cleaned: string = contact.trim()
    if (EMAIL_PATTERN.test(cleaned)) return `mailto:${cleaned}`
    if (PHONE_PATTERN.test(cleaned)) return `tel:${cleaned.replace(/[^\d+]/g, '')}`
    return null
  }

  /**
   * A Google Maps link that finds a place from its name and address.
   * @param place - What to look for (« Toitures Morel, 12 rue des Lilas, Rennes »).
   * @returns The Maps search link.
   */
  static mapHref(place: string): string {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(place.trim())}`
  }
}
