// The spaced hyphen, en dash or em dash before the descriptive part of a Maps listing.
const DESCRIPTION_SEPARATOR: RegExp = /\s+[-–—]\s+/

/**
 * Business names as the public pages show them.
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
}
