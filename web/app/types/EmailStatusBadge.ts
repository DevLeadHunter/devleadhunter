import type { EmailStatus } from '~/types'

/**
 * Props for the EmailStatusBadge component.
 */
export type EmailStatusBadgeProps = {
  /** Email status value from the backend EmailStatus enum. */
  status: EmailStatus
}
