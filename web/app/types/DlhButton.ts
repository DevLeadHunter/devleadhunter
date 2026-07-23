/** Visual variant of a DlhButton. */
export type DlhButtonVariant = 'primary' | 'secondary' | 'danger'

/** Size of a DlhButton. */
export type DlhButtonSize = 'md' | 'lg'

/** Native button type of a DlhButton. */
export type DlhButtonType = 'button' | 'submit' | 'reset'

/**
 * Props for the UiDlhButton component.
 */
export type DlhButtonProps = {
  /** Visual variant. */
  variant?: DlhButtonVariant
  /** Button size. */
  size?: DlhButtonSize
  /** Native button type. */
  type?: DlhButtonType
  /** Whether the button is disabled. */
  disabled?: boolean
  /** Whether a spinner replaces normal interaction. */
  loading?: boolean
  /** Extra classes appended to the button. */
  class?: string
}
