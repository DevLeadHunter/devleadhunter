import type { EmailLog, EmailTemplate, Prospect, User } from '~/types'
import type { Order } from '~/services/ordersService'
import type { SmsMessage } from '~/services/smsService'
import type { SearchProspectsPrefill } from '~/types/SearchProspectsDrawer'
import type { CampaignDetailResponse } from '~/services/campaignService'

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
  /** Open straight on the edit form (pencil action of the prospect table). */
  startInEdit?: boolean
}

/** Prospect settings sub-drawer (source URLs + « ne plus contacter »), stacked over the detail drawer. */
export type ProspectSettingsDrawerEntry = {
  kind: 'prospect-settings'
  prospect: Prospect
}

/** Step taken by the prospect drawer inside the list it browses. */
export type DrawerBrowseDirection = 'previous' | 'next'

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

/** Prefilled values of the SMS composer (e.g. a self-test number). */
export type SendSmsPrefill = {
  to: string
  recipient_name: string
  text: string
}

export type SendSmsDrawerEntry = {
  kind: 'send-sms'
  prospect: Prospect | null
  prefill?: SendSmsPrefill
}

export type EmailLogDrawerEntry = {
  kind: 'email-log'
  log: EmailLog
  campaignName: string | undefined
}

export type SmsLogDrawerEntry = {
  kind: 'sms-log'
  message: SmsMessage
}

/** Sub-page of a failed email log: re-send the same message to a corrected address. */
export type EmailResendDrawerEntry = {
  kind: 'email-resend'
  log: EmailLog
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

export type CampaignFormDrawerMode = 'create' | 'edit'

export type CampaignFormDrawerEntry = {
  kind: 'campaign-form'
  mode: CampaignFormDrawerMode
  campaign: CampaignDetailResponse | null
}

export type AddProspectDrawerEntry = {
  kind: 'add-prospect'
}

export type SearchProspectsDrawerEntry = {
  kind: 'search-prospects'
  prefill?: SearchProspectsPrefill
}

/** Picker attaching existing prospects to a campaign (from its Prospects tab). */
export type CampaignProspectsPickerDrawerEntry = {
  kind: 'campaign-prospects-picker'
  campaignId: number
  existingProspectIds: number[]
}

export type SendPolicyDrawerEntry = {
  kind: 'send-policy'
}

export type OrderDrawerMode = 'create' | 'view'

export type OrderDrawerEntry = {
  kind: 'order'
  order: Order | null
  mode: OrderDrawerMode
}

export type UserFormDrawerMode = 'create' | 'edit'

export type UserFormDrawerEntry = {
  kind: 'user-form'
  mode: UserFormDrawerMode
  user: User | null
}

/** Sale finalization: reviewed billing details → invoice → sale email. */
export type FinalizeSaleDrawerEntry = {
  kind: 'finalize-sale'
  order: Order
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
  | ProspectSettingsDrawerEntry
  | SendEmailDrawerEntry
  | SendSmsDrawerEntry
  | EmailLogDrawerEntry
  | SmsLogDrawerEntry
  | EmailResendDrawerEntry
  | EmailTemplateDrawerEntry
  | EmailSignaturesDrawerEntry
  | ProfileDrawerEntry
  | OrganizationDrawerEntry
  | CampaignFormDrawerEntry
  | AddProspectDrawerEntry
  | SearchProspectsDrawerEntry
  | CampaignProspectsPickerDrawerEntry
  | SendPolicyDrawerEntry
  | CoverageFiltersDrawerEntry
  | CoverageProspectsDrawerEntry
  | OrderDrawerEntry
  | FinalizeSaleDrawerEntry
  | UserFormDrawerEntry

/** Cross-page notice describing the latest prospect mutation done from a drawer. */
export type ProspectMutationNotice = { type: 'updated'; prospect: Prospect } | { type: 'deleted'; prospectId: number }

/** Cross-page notice describing the latest order mutation done from a drawer. */
export type OrderMutationNotice = { type: 'updated'; order: Order } | { type: 'deleted'; orderId: number }
