const COMBINING_ACCENTS: RegExp = /[̀-ͯ]/g

/**
 * Text compared without its case and accents (« Électricien » reads as « electricien »).
 */
export class TextFoldUtils {
  /**
   * The text lower-cased and without diacritics.
   * @param value - The text.
   * @returns The folded text.
   */
  static fold(value: string): string {
    return value.normalize('NFD').replace(COMBINING_ACCENTS, '').toLowerCase()
  }
}
