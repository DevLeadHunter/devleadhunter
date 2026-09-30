// The spaced hyphen, en dash or em dash before the descriptive part of a Maps listing.
// A French word starting with a vowel or a mute h takes « d' » (« d'Atelier ») rather than « de ».
const FRENCH_ELISION_START: RegExp = /^[aeiouyàâäéèêëîïôöùûüh]/i
const DESCRIPTION_SEPARATOR: RegExp = /\s+[-–—]\s+/

/**
 * Business names and headings as the public pages show them.
 */
export class BusinessNameUtils {
  /**
   * The business name without the descriptive « - » part of its Maps listing (« Toitures Morel »).
   * @param name - The business name, as listed.
   * @returns The part before the first spaced dash, trimmed; the whole name when that part is empty.
   */
  static short(name: string): string {
    return name.split(DESCRIPTION_SEPARATOR)[0]?.trim() || name
  }

  /**
   * The business's trade and town as one heading line (« Couvreur à Rennes »).
   * @param tradeLabel - The Google Maps category, or null.
   * @param city - The town, or null.
   * @returns The line; the known part alone when the other is missing, empty when both are.
   */
  static tradeAndCity(tradeLabel: string | null, city: string | null): string {
    const trade: string = (tradeLabel ?? '').trim()
    const town: string = (city ?? '').trim()
    if (trade && town) return `${trade} à ${town}`
    return trade || town
  }

  /**
   * What follows the business's name inside a sentence (« , couvreur à Rennes », « à Rennes »).
   * @param tradeLabel - The Google Maps category, or null.
   * @param city - The town, or null.
   * @returns The phrase, empty when both are unknown.
   */
  static tradeAndCityAfterName(tradeLabel: string | null, city: string | null): string {
    const trade: string = (tradeLabel ?? '').trim()
    const town: string = (city ?? '').trim()
    const place: string = town ? ` à ${town}` : ''
    if (!trade) return place
    return `, ${trade.charAt(0).toLocaleLowerCase('fr-FR')}${trade.slice(1)}${place}`
  }

  /**
   * The « de » a French noun takes before the business name, elided before a vowel (« de », « d' »).
   * @param name - The business name.
   * @returns « d' » or « de » followed by a space.
   */
  static preposition(name: string): string {
    return FRENCH_ELISION_START.test(name) ? "d'" : 'de '
  }

  /**
   * The business as the complement of a French noun (« de Toitures Morel », « d'Atelier Morel »).
   * @param name - The business name.
   * @returns The name with its « de » or « d' ».
   */
  static ofBusiness(name: string): string {
    return `${BusinessNameUtils.preposition(name)}${name}`
  }
}
