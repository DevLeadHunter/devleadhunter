import type { EmailStatus } from '~/types'

/**
 * Props for the EmailStatusBadge component.
 */
export interface EmailStatusBadgeProps {
  /** Email status value from the backend EmailStatus enum. */
  status: EmailStatus
}
