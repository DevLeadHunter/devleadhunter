// No « ? » nor « & »: an address may not smuggle a header (« ?bcc=… ») into the mailto link.
const EMAIL_PATTERN: RegExp = /^[^@\s?&]+@[^@\s?&]+\.[^@\s?&]+$/
const PHONE_PATTERN: RegExp = /^\+?[\d\s.()-]{6,}$/

/**
 * Tap-to-call and tap-to-mail links for the contacts visitors leave.
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
}
