/** Loose shape of an email address, enough to tell it from a phone number. */
const EMAIL_PATTERN: RegExp = /^[^\s@?&]+@[^\s@?&]+\.[^\s@?&]+$/

/** What a phone number may contain once typed by a visitor: digits, a leading plus, separators. */
const PHONE_PATTERN: RegExp = /^\+?[\d\s().-]{6,}$/

/**
 * The link that reaches a contact a visitor typed: `mailto:` for an address, `tel:` for a number.
 * @param contact - The contact as the visitor typed it.
 * @returns The href, or null when the text is neither an address nor a number.
 */
export function contactHref(contact: string): string | null {
  const cleaned: string = contact.trim()
  if (EMAIL_PATTERN.test(cleaned)) return `mailto:${cleaned}`
  if (PHONE_PATTERN.test(cleaned)) return `tel:${cleaned.replace(/[\s().-]/g, '')}`
  return null
}
