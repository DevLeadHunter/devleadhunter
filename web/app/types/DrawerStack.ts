import type { EmailLog, EmailTemplate, Prospect } from '~/types'
import type { SearchProspectsPrefill } from '~/types/SearchProspectsDrawer'

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
export type ProspectDrawerEntry = {
  kind: 'prospect'
  prospect: Prospect
}

/** Prefilled values of the email composer (e.g. « Renvoyer » from a log). */
export type SendEmailPrefill = {
  recipient_email: string
  recipient_name: string
  subject: string
  body: string
}

/** Manual email composer drawer entry. */
export type SendEmailDrawerEntry = {
  kind: 'send-email'
  prospect: Prospect | null
  prefill?: SendEmailPrefill
}

/** Email log detail drawer entry. */
export type EmailLogDrawerEntry = {
  kind: 'email-log'
  log: EmailLog
  campaignName: string | undefined
}

/** Mode of the email template drawer. */
export type EmailTemplateDrawerMode = 'create' | 'edit' | 'preview'

/** Email template create/edit/preview drawer entry. */
export type EmailTemplateDrawerEntry = {
  kind: 'email-template'
  mode: EmailTemplateDrawerMode
  template: EmailTemplate | null
}

/** Email signatures management drawer entry. */
export type EmailSignaturesDrawerEntry = {
  kind: 'email-signatures'
}

/** User profile edit drawer entry. */
export type ProfileDrawerEntry = {
  kind: 'profile'
}

/** Organization (team) management drawer entry. */
export type OrganizationDrawerEntry = {
  kind: 'organization'
}

/** Campaign creation drawer entry. */
export type CreateCampaignDrawerEntry = {
  kind: 'create-campaign'
}

/** Manual prospect creation drawer entry. */
export type AddProspectDrawerEntry = {
  kind: 'add-prospect'
}

/** Prospect search (scraping) drawer entry. */
export type SearchProspectsDrawerEntry = {
  kind: 'search-prospects'
  prefill?: SearchProspectsPrefill
}

/** Send-policy (email cadence) drawer entry. */
export type SendPolicyDrawerEntry = {
  kind: 'send-policy'
}

/** A zone of the coverage map (one city, or a region's covered cities). */
export type CoverageZone = {
  kind: 'city' | 'region'
  label: string
  cities: string[]
  prefillCity?: string
}

/** Coverage-map filters drawer entry (trades + zones to attack). */
export type CoverageFiltersDrawerEntry = {
  kind: 'coverage-filters'
}

/** Coverage-map zone prospects drawer entry. */
export type CoverageProspectsDrawerEntry = {
  kind: 'coverage-prospects'
  zone: CoverageZone
}

/** One entry of the persistent drawer stack. */
export type DrawerStackEntry =
  | ProspectDrawerEntry
  | SendEmailDrawerEntry
  | EmailLogDrawerEntry
  | EmailTemplateDrawerEntry
  | EmailSignaturesDrawerEntry
  | ProfileDrawerEntry
  | OrganizationDrawerEntry
  | CreateCampaignDrawerEntry
  | AddProspectDrawerEntry
  | SearchProspectsDrawerEntry
  | SendPolicyDrawerEntry
  | CoverageFiltersDrawerEntry
  | CoverageProspectsDrawerEntry

/** Cross-page notice describing the latest prospect mutation done from a drawer. */
export type ProspectMutationNotice = { type: 'updated'; prospect: Prospect } | { type: 'deleted'; prospectId: number }
