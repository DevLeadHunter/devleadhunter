const EMAIL_PATTERN: RegExp = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

/**
 * Validation rules for the fields of the marketing site's forms.
 */
export class FieldsValidation {
  /**
   * Check that a field holds more than blank characters.
   * @param value - The value the visitor typed.
   * @returns Whether the field is filled.
   */
  static isFilled(value: string): boolean {
    return value.trim() !== ''
  }

  /**
   * Check that a value looks like an email address.
   * @param value - The value the visitor typed.
   * @returns Whether the value has the shape of an email address.
   */
  static isEmail(value: string): boolean {
    return EMAIL_PATTERN.test(value.trim())
  }
}
