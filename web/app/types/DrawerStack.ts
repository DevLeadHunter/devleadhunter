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

/** Presenter (webcam) clip management drawer entry — prospection videos. */
export interface PresenterVideoDrawerEntry {
  kind: 'presenter-video'
}

/** Campaign creation drawer entry. */
export interface CreateCampaignDrawerEntry {
  kind: 'create-campaign'
}

/** Manual prospect creation drawer entry. */
export interface AddProspectDrawerEntry {
  kind: 'add-prospect'
}

/** Prospect search (scraping) drawer entry. */
export interface SearchProspectsDrawerEntry {
  kind: 'search-prospects'
  /** Optional form prefill (e.g. « Prospecter » a suggested city on the coverage map). */
  prefill?: SearchProspectsPrefill
}

/** Send-policy (email cadence) drawer entry. */
export interface SendPolicyDrawerEntry {
  kind: 'send-policy'
}

/** A zone of the coverage map (one city, or a region's covered cities). */
export interface CoverageZone {
  /** Zone granularity. */
  kind: 'city' | 'region'
  /** Display label (« Rennes », « Bretagne »). */
  label: string
  /** Covered city names queried for the prospect list. */
  cities: string[]
  /** City prefilled by the « Prospecter à nouveau ici » action. */
  prefillCity?: string
}

/** Coverage-map filters drawer entry (trades + zones to attack). */
export interface CoverageFiltersDrawerEntry {
  kind: 'coverage-filters'
}

/** Coverage-map zone prospects drawer entry. */
export interface CoverageProspectsDrawerEntry {
  kind: 'coverage-prospects'
  zone: CoverageZone
}

/** One entry of the persistent drawer stack. */
export type DrawerStackEntry =
  | ProspectDrawerEntry
  | SendEmailDrawerEntry
  | EmailLogDrawerEntry
  | EmailTemplateDrawerEntry
  | ProfileDrawerEntry
  | OrganizationDrawerEntry
  | PresenterVideoDrawerEntry
  | CreateCampaignDrawerEntry
  | AddProspectDrawerEntry
  | SearchProspectsDrawerEntry
  | SendPolicyDrawerEntry
  | CoverageFiltersDrawerEntry
  | CoverageProspectsDrawerEntry

/** Cross-page notice describing the latest prospect mutation done from a drawer. */
export type ProspectMutationNotice = { type: 'updated'; prospect: Prospect } | { type: 'deleted'; prospectId: number }
