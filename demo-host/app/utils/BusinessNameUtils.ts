// The spaced hyphen, en dash or em dash before the descriptive part of a Maps listing.
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
}
