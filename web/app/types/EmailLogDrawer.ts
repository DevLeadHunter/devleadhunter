import type { EmailLog } from '~/types'

/**
 * Props for the EmailLogDrawer component.
 */
export type EmailLogDrawerProps = {
  /** Whether the drawer is visible. */
  open: boolean
  /** Email log entry to display, or ``null`` when nothing is selected. */
  log: EmailLog | null
  /** Display name of the campaign the log belongs to (optional). */
  campaignName?: string
}
