import type { EmailLog, EmailTemplate, Prospect } from '~/types'

/**
 * Entries of the persistent right-side drawer stack.
 *
 * The stack lives in the `drawerStack` Pinia store and is rendered once by
 * `UiDrawerStackHost` inside the dashboard layout, so an open drawer survives
 * page navigation. Pushing a drawer of a different kind stacks it on top of
 * the current one (with a back affordance); pushing the same kind replaces
 * the top entry.
 */

/** Prospect detail drawer entry. */
export interface ProspectDrawerEntry {
  kind: 'prospect'
  /** Prospect displayed by the drawer. */
  prospect: Prospect
}

/** Prefilled values of the email composer (e.g. « Renvoyer » from a log). */
export interface SendEmailPrefill {
  recipient_email: string
  recipient_name: string
  subject: string
  body: string
}

/** Manual email composer drawer entry. */
export interface SendEmailDrawerEntry {
  kind: 'send-email'
  /** Prefilled recipient (null opens a blank composer). */
  prospect: Prospect | null
  /** Explicit prefill overriding the prospect-derived values. */
  prefill?: SendEmailPrefill
}

/** Email log detail drawer entry. */
export interface EmailLogDrawerEntry {
  kind: 'email-log'
  /** Log displayed by the drawer. */
  log: EmailLog
  /** Resolved campaign name (display only). */
  campaignName: string | undefined
}

/** Mode of the email template drawer. */
export type EmailTemplateDrawerMode = 'create' | 'edit' | 'preview'

/** Email template create/edit/preview drawer entry. */
export interface EmailTemplateDrawerEntry {
  kind: 'email-template'
  /** Drawer mode. */
  mode: EmailTemplateDrawerMode
  /** Template being edited or previewed (null in create mode). */
  template: EmailTemplate | null
}

/** User profile edit drawer entry. */
export interface ProfileDrawerEntry {
  kind: 'profile'
}

/** Organization (team) management drawer entry. */
export interface OrganizationDrawerEntry {
  kind: 'organization'
}

/** One entry of the persistent drawer stack. */
export type DrawerStackEntry =
  | ProspectDrawerEntry
  | SendEmailDrawerEntry
  | EmailLogDrawerEntry
  | EmailTemplateDrawerEntry
  | ProfileDrawerEntry
  | OrganizationDrawerEntry

/** Cross-page notice describing the latest prospect mutation done from a drawer. */
export type ProspectMutationNotice = { type: 'updated'; prospect: Prospect } | { type: 'deleted'; prospectId: number }
