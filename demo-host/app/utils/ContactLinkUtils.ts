// No « ? » nor « & »: an address may not smuggle a header (« ?bcc=… ») into the mailto link.
const EMAIL_PATTERN: RegExp = /^[^@\s?&]+@[^@\s?&]+\.[^@\s?&]+$/
const PHONE_PATTERN: RegExp = /^\+?[\d\s.()-]{6,}$/
const WEBSITE_SCHEME_PATTERN: RegExp = /^https?:\/\//i
const LEADING_WWW_PATTERN: RegExp = /^www\./i

/**
 * Tap-to-call, tap-to-mail, website and map links for the contacts on the public pages.
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

  /**
   * An absolute link to a website saved with or without its scheme (« dibodev.fr »).
   * @param website - The website address of a profile.
   * @returns The http(s) link, or an empty string without an address.
   */
  static websiteHref(website: string | null | undefined): string {
    const cleaned: string = (website ?? '').trim()
    if (!cleaned) return ''
    return WEBSITE_SCHEME_PATTERN.test(cleaned) ? cleaned : `https://${cleaned}`
  }

  /**
   * The bare domain of a website, as written in a sentence (« dibodev.fr »).
   * @param website - The website address of a profile.
   * @returns The domain without « www. », or an empty string when the address is not a valid link.
   */
  static websiteDomain(website: string | null | undefined): string {
    const href: string = ContactLinkUtils.websiteHref(website)
    if (!href) return ''

    try {
      return new URL(href).hostname.replace(LEADING_WWW_PATTERN, '')
    } catch {
      return ''
    }
  }
}
