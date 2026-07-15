/**
 * Props for the UiConfirmModal component.
 */
export interface UiConfirmModalProps {
  /** Modal title. */
  title?: string
  /** Confirmation message. */
  message?: string
  /** Label of the confirm (destructive) button. */
  confirmText?: string
  /** Label of the cancel button. */
  cancelText?: string
}
