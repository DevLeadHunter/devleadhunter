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

export type SendEmailDrawerEntry = {
  kind: 'send-email'
  prospect: Prospect | null
  prefill?: SendEmailPrefill
}

export type EmailLogDrawerEntry = {
  kind: 'email-log'
  log: EmailLog
  campaignName: string | undefined
}

export type EmailTemplateDrawerMode = 'create' | 'edit' | 'preview'

export type EmailTemplateDrawerEntry = {
  kind: 'email-template'
  mode: EmailTemplateDrawerMode
  template: EmailTemplate | null
}

export type EmailSignaturesDrawerEntry = {
  kind: 'email-signatures'
}

export type ProfileDrawerEntry = {
  kind: 'profile'
}

export type OrganizationDrawerEntry = {
  kind: 'organization'
}

export type CreateCampaignDrawerEntry = {
  kind: 'create-campaign'
}

export type AddProspectDrawerEntry = {
  kind: 'add-prospect'
}

export type SearchProspectsDrawerEntry = {
  kind: 'search-prospects'
  prefill?: SearchProspectsPrefill
}

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
