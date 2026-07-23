/**
 * Visual appearance of the password input:
 * - 'app': dashboard surfaces — themed by the `--app-*` variables (`input-field`).
 * - 'landing': marketing/auth surfaces — fixed paper DA (`landing-input`).
 */
export type UiPasswordInputAppearance = 'app' | 'landing'

export type UiPasswordInputProps = {
  id: string
  modelValue: string
  placeholder?: string
  required?: boolean
  hasError?: boolean
  appearance?: UiPasswordInputAppearance
}
