/**
 * Visual appearance of the password input:
 * - 'app': dashboard surfaces — themed by the `--app-*` variables (`input-field`).
 * - 'landing': marketing/auth surfaces — fixed paper DA (`landing-input`).
 */
export type UiPasswordInputAppearance = 'app' | 'landing'

/** Props for the UiPasswordInput component. */
export type UiPasswordInputProps = {
  /** Id attribute forwarded to the native input (pairs with the label). */
  id: string
  /** Controlled value (v-model). */
  modelValue: string
  /** Native placeholder text. */
  placeholder?: string
  /** Native required flag. */
  required?: boolean
  /** Paints the error border when true. */
  hasError?: boolean
  /** Visual theme of the field. */
  appearance?: UiPasswordInputAppearance
}
