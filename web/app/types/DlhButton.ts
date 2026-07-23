/** Visual variant of a DlhButton. */
export type DlhButtonVariant = 'primary' | 'secondary' | 'danger'

/** Size of a DlhButton. */
export type DlhButtonSize = 'md' | 'lg'

/** Native button type of a DlhButton. */
export type DlhButtonType = 'button' | 'submit' | 'reset'

export type DlhButtonProps = {
  variant?: DlhButtonVariant
  size?: DlhButtonSize
  type?: DlhButtonType
  disabled?: boolean
  loading?: boolean
  class?: string
}
