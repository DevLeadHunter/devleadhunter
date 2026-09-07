<template>
  <div>
    <UiProspectDrawer
      ref="prospectDrawer"
      :open="prospectEntry !== null"
      :prospect="prospectEntry?.prospect ?? null"
      :start-in-edit="prospectEntry?.startInEdit ?? false"
      :browse-position-label="browsePositionLabel"
      :can-browse-previous="canBrowsePrevious"
      :can-browse-next="canBrowseNext"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @browse-previous="browseToProspect('previous')"
      @browse-next="browseToProspect('next')"
      @updated="handleProspectUpdated"
      @deleted="handleProspectDeleted"
      @send-email="handleSendEmail"
      @send-sms="handleSendSms"
      @mark-as-sold="handleMarkAsSold"
      @toggle-contacted="handleToggleContacted"
      @open-settings="handleOpenProspectSettings"
    />

    <UiProspectSettingsDrawer
      :open="prospectSettingsEntry !== null"
      :prospect="prospectSettingsEntry?.prospect ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="handleProspectUpdated"
    />

    <UiSendEmailDrawer
      :open="sendEmailEntry !== null"
      :prospect="sendEmailEntry?.prospect ?? null"
      :prefill="sendEmailEntry?.prefill ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @sent="handleEmailSent"
    />

    <UiSendSmsDrawer
      :open="sendSmsEntry !== null"
      :prospect="sendSmsEntry?.prospect ?? null"
      :prefill="sendSmsEntry?.prefill ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @sent="handleSmsSent"
    />

    <UiEmailLogDrawer
      :open="emailLogEntry !== null"
      :log="emailLogEntry?.log ?? null"
      :campaign-name="emailLogEntry?.campaignName"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @resend="handleResendEmail"
      @retry="handleOpenResend"
    />

    <UiSmsLogDrawer
      :open="smsLogEntry !== null"
      :message="smsLogEntry?.message ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @resend="handleResendSms"
    />

    <UiEmailResendDrawer
      :open="emailResendEntry !== null"
      :log="emailResendEntry?.log ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @resent="handleEmailResent"
    />

    <UiEmailTemplateDrawer
      :open="emailTemplateEntry !== null"
      :mode="emailTemplateEntry?.mode ?? 'create'"
      :template="emailTemplateEntry?.template ?? null"
      :show-back="hasPrevious"
      :browse-position-label="templateBrowsePositionLabel"
      :can-browse-previous="canBrowsePreviousTemplate"
      :can-browse-next="canBrowseNextTemplate"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleTemplateSaved"
      @edit="handleTemplateEdit"
      @browse-previous="browseToTemplate('previous')"
      @browse-next="browseToTemplate('next')"
    />

    <UiEmailSignaturesDrawer
      :open="emailSignaturesEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiProfileDrawer
      :open="profileEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiOrganizationDrawer
      :open="organizationEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCampaignDrawer
      :open="campaignFormEntry !== null"
      :mode="campaignFormEntry?.mode ?? 'create'"
      :campaign="campaignFormEntry?.campaign ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleCampaignSaved"
    />

    <UiAddProspectDrawer
      :open="addProspectEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @created="handleProspectCreated"
    />

    <UiSearchProspectsDrawer
      :open="searchProspectsEntry !== null"
      :show-back="hasPrevious"
      :prefill="searchProspectsEntry?.prefill ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCampaignProspectsPickerDrawer
      :open="campaignProspectsPickerEntry !== null"
      :show-back="hasPrevious"
      :campaign-id="campaignProspectsPickerEntry?.campaignId ?? null"
      :existing-prospect-ids="campaignProspectsPickerEntry?.existingProspectIds ?? []"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @added="handleCampaignProspectsAdded"
    />

    <UiSendPolicyDrawer
      :open="sendPolicyEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCoverageFiltersDrawer
      :open="coverageFiltersEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiCoverageProspectsDrawer
      :open="coverageProspectsEntry !== null"
      :show-back="hasPrevious"
      :zone="coverageProspectsEntry?.zone ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <UiOrderDrawer
      :open="orderEntry !== null"
      :order="orderEntry?.order ?? null"
      :mode="orderEntry?.mode ?? 'view'"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="drawerStack.notifyOrderUpdated"
      @created="handleOrderCreated"
      @deleted="handleOrderDeleted"
      @finalize="handleFinalizeSale"
    />

    <UiFinalizeSaleDrawer
      :open="finalizeSaleEntry !== null"
      :order="finalizeSaleEntry?.order ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="drawerStack.notifyOrderUpdated"
    />

    <UiUserFormDrawer
      :open="userFormEntry !== null"
      :mode="userFormEntry?.mode ?? 'create'"
      :user="userFormEntry?.user ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleUserSaved"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import type {
  AddProspectDrawerEntry,
  CampaignProspectsPickerDrawerEntry,
  CoverageFiltersDrawerEntry,
  CoverageProspectsDrawerEntry,
  CampaignFormDrawerEntry,
  EmailLogDrawerEntry,
  EmailResendDrawerEntry,
  EmailSignaturesDrawerEntry,
  EmailTemplateDrawerEntry,
  FinalizeSaleDrawerEntry,
  OrderDrawerEntry,
  OrganizationDrawerEntry,
  ProfileDrawerEntry,
  DrawerBrowseDirection,
  ProspectDrawerEntry,
  ProspectSettingsDrawerEntry,
  SearchProspectsDrawerEntry,
  SendEmailDrawerEntry,
  SendSmsDrawerEntry,
  SmsLogDrawerEntry,
  SendPolicyDrawerEntry,
  UserFormDrawerEntry,
} from '~/types/DrawerStack'
import type { SmsMessage } from '~/services/smsService'
import type { EmailTemplate, Prospect } from '~/types'
import type { Order } from '~/services/ordersService'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useMediaQuery } from '@vueuse/core'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { ProspectsService } from '~/services/prospectsService'
import { OrdersService } from '~/services/ordersService'
import { useToast } from '~/composables/useToast'
import { useHorizontalSwipe } from '~/composables/useHorizontalSwipe'

const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const toast: UseToastReturn = useToast()

/** Matches the dashboard's mobile breakpoint (md = 768px) so swipe gestures stay mobile-only. */
const isMobile: ComputedRef<boolean> = useMediaQuery('(max-width: 767px)')

/** Prospect drawer instance — read to suspend swipe-to-next while its edit form is open. */
const prospectDrawer: Ref<{ editMode: boolean } | null> = ref(null)

/** Top entry narrowed to the prospect drawer (null when another kind is on top). */
const prospectEntry: ComputedRef<ProspectDrawerEntry | null> = computed((): ProspectDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'prospect' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the prospect settings sub-drawer. */
const prospectSettingsEntry: ComputedRef<ProspectSettingsDrawerEntry | null> = computed(
  (): ProspectSettingsDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'prospect-settings' ? drawerStack.topEntry : null
  },
)

/**
 * Open the settings sub-drawer stacked over the prospect detail drawer.
 * @param prospect - The prospect whose settings are edited.
 */
function handleOpenProspectSettings(prospect: Prospect): void {
  drawerStack.push({ kind: 'prospect-settings', prospect })
}

/** Top entry narrowed to the send-email drawer. */
const sendEmailEntry: ComputedRef<SendEmailDrawerEntry | null> = computed((): SendEmailDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-email' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the send-sms drawer. */
const sendSmsEntry: ComputedRef<SendSmsDrawerEntry | null> = computed((): SendSmsDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-sms' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the sms-log drawer. */
const smsLogEntry: ComputedRef<SmsLogDrawerEntry | null> = computed((): SmsLogDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'sms-log' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-log drawer. */
const emailLogEntry: ComputedRef<EmailLogDrawerEntry | null> = computed((): EmailLogDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'email-log' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the failed-email resend sub-drawer. */
const emailResendEntry: ComputedRef<EmailResendDrawerEntry | null> = computed((): EmailResendDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'email-resend' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-template drawer. */
const emailTemplateEntry: ComputedRef<EmailTemplateDrawerEntry | null> = computed(
  (): EmailTemplateDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'email-template' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the email-signatures drawer. */
const emailSignaturesEntry: ComputedRef<EmailSignaturesDrawerEntry | null> = computed(
  (): EmailSignaturesDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'email-signatures' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the profile drawer. */
const profileEntry: ComputedRef<ProfileDrawerEntry | null> = computed((): ProfileDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'profile' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the organization drawer. */
const organizationEntry: ComputedRef<OrganizationDrawerEntry | null> = computed((): OrganizationDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'organization' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the campaign create/edit drawer. */
const campaignFormEntry: ComputedRef<CampaignFormDrawerEntry | null> = computed((): CampaignFormDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'campaign-form' ? drawerStack.topEntry : null
})

/** Campaign renamed from its drawer — refresh the page behind, then leave the stack. */
function handleCampaignSaved(): void {
  drawerStack.bumpCampaignsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Top entry narrowed to the manual prospect creation drawer. */
const addProspectEntry: ComputedRef<AddProspectDrawerEntry | null> = computed((): AddProspectDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'add-prospect' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the prospect search drawer. */
const searchProspectsEntry: ComputedRef<SearchProspectsDrawerEntry | null> = computed(
  (): SearchProspectsDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'search-prospects' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the campaign prospects picker drawer. */
const campaignProspectsPickerEntry: ComputedRef<CampaignProspectsPickerDrawerEntry | null> = computed(
  (): CampaignProspectsPickerDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'campaign-prospects-picker' ? drawerStack.topEntry : null
  },
)

/** Prospects attached to the campaign — refresh the page behind, then leave the stack. */
function handleCampaignProspectsAdded(): void {
  drawerStack.bumpCampaignsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Top entry narrowed to the send-policy drawer. */
const sendPolicyEntry: ComputedRef<SendPolicyDrawerEntry | null> = computed((): SendPolicyDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-policy' ? drawerStack.topEntry : null
})

/** Coverage-map filters entry when it is the top of the stack. */
const coverageFiltersEntry: ComputedRef<CoverageFiltersDrawerEntry | null> = computed(
  (): CoverageFiltersDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'coverage-filters' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the order drawer. */
const orderEntry: ComputedRef<OrderDrawerEntry | null> = computed((): OrderDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'order' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the sale finalization drawer. */
const finalizeSaleEntry: ComputedRef<FinalizeSaleDrawerEntry | null> = computed((): FinalizeSaleDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'finalize-sale' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the user create/edit drawer. */
const userFormEntry: ComputedRef<UserFormDrawerEntry | null> = computed((): UserFormDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'user-form' ? drawerStack.topEntry : null
})

/** User saved from its drawer — refresh the list page, then leave the stack. */
function handleUserSaved(): void {
  drawerStack.bumpUsersRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Stack the sale finalization on top of the order drawer. */
function handleFinalizeSale(): void {
  const entry: OrderDrawerEntry | null = orderEntry.value
  if (entry?.order) drawerStack.push({ kind: 'finalize-sale', order: entry.order })
}

/**
 * New sale saved from the create drawer — refresh lists and show the created order.
 * @param order - The freshly created order.
 */
function handleOrderCreated(order: Order): void {
  drawerStack.notifyOrderUpdated(order)
  drawerStack.push({ kind: 'order', order, mode: 'view' })
}

/**
 * Order deleted from its drawer — drop it from the stack and close.
 * @param orderId - Identifier of the deleted order.
 */
function handleOrderDeleted(orderId: number): void {
  drawerStack.notifyOrderDeleted(orderId)
  drawerStack.closeAll()
}

/** Coverage-map zone prospects entry when it is the top of the stack. */
const coverageProspectsEntry: ComputedRef<CoverageProspectsDrawerEntry | null> = computed(
  (): CoverageProspectsDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'coverage-prospects' ? drawerStack.topEntry : null
  },
)

/**
 * Prospect created from the add drawer — notify pages (list insert) and chain
 * straight to the new prospect's detail drawer.
 * @param created - The freshly created prospect.
 */
function handleProspectCreated(created: Prospect): void {
  drawerStack.notifyProspectUpdated(created)
  drawerStack.push({ kind: 'prospect', prospect: created })
}

/** Whether the back affordance should be visible on the top drawer. */
const hasPrevious: ComputedRef<boolean> = computed((): boolean => drawerStack.hasPrevious)

/**
 * Prospect edited from the drawer — refresh the stack and notify pages.
 * @param updated - The freshly updated prospect.
 */
function handleProspectUpdated(updated: Prospect): void {
  drawerStack.notifyProspectUpdated(updated)
}

/** Position of the open prospect in the browsed list, -1 when that list is unknown. */
const browseIndex: ComputedRef<number> = computed((): number => {
  const openId: number | undefined = prospectEntry.value?.prospect.id
  if (openId === undefined) return -1
  return drawerStack.prospectBrowseList.findIndex((candidate: Prospect): boolean => candidate.id === openId)
})

const browsePositionLabel: ComputedRef<string> = computed((): string =>
  browseIndex.value < 0 ? '' : `${browseIndex.value + 1} / ${drawerStack.prospectBrowseList.length}`,
)

const canBrowsePrevious: ComputedRef<boolean> = computed((): boolean => browseIndex.value > 0)

const canBrowseNext: ComputedRef<boolean> = computed(
  (): boolean => browseIndex.value >= 0 && browseIndex.value < drawerStack.prospectBrowseList.length - 1,
)

/**
 * Open the neighbouring prospect of the browsed list, keeping the drawer in place.
 * @param direction - Which neighbour to open.
 */
function browseToProspect(direction: DrawerBrowseDirection): void {
  const step: number = direction === 'previous' ? -1 : 1
  const target: Prospect | undefined = drawerStack.prospectBrowseList[browseIndex.value + step]
  if (target) drawerStack.push({ kind: 'prospect', prospect: target })
}

/** Position of the previewed template in the browsed list, -1 when that list is unknown. */
const templateBrowseIndex: ComputedRef<number> = computed((): number => {
  // Only the preview steps through the list — editing one template at a time is deliberate.
  if (emailTemplateEntry.value?.mode !== 'preview') return -1
  const openId: number | undefined = emailTemplateEntry.value.template?.id
  if (openId === undefined) return -1
  return drawerStack.emailTemplateBrowseList.findIndex((candidate: EmailTemplate): boolean => candidate.id === openId)
})

const templateBrowsePositionLabel: ComputedRef<string> = computed((): string =>
  templateBrowseIndex.value < 0
    ? ''
    : `${templateBrowseIndex.value + 1} / ${drawerStack.emailTemplateBrowseList.length}`,
)

const canBrowsePreviousTemplate: ComputedRef<boolean> = computed((): boolean => templateBrowseIndex.value > 0)

const canBrowseNextTemplate: ComputedRef<boolean> = computed(
  (): boolean =>
    templateBrowseIndex.value >= 0 && templateBrowseIndex.value < drawerStack.emailTemplateBrowseList.length - 1,
)

/**
 * Preview the neighbouring template of the browsed list, keeping the drawer in place.
 * @param direction - Which neighbour to open.
 */
function browseToTemplate(direction: DrawerBrowseDirection): void {
  const step: number = direction === 'previous' ? -1 : 1
  const target: EmailTemplate | undefined = drawerStack.emailTemplateBrowseList[templateBrowseIndex.value + step]
  if (target) drawerStack.push({ kind: 'email-template', mode: 'preview', template: target })
}

/**
 * Prospect deleted from its drawer — drop it from the stack and notify pages.
 * @param prospectId - Identifier of the deleted prospect.
 */
function handleProspectDeleted(prospectId: number): void {
  drawerStack.notifyProspectDeleted(prospectId)
}

/**
 * « Email » action — stack the composer on top of the prospect drawer.
 * @param prospect - The prospect used to prefill the composer.
 */
function handleSendEmail(prospect: Prospect): void {
  drawerStack.push({ kind: 'send-email', prospect })
}

/**
 * « Marquer comme vendu » action — create the order then open the sales page.
 * @param prospect - The prospect being marked as sold.
 */
async function handleMarkAsSold(prospect: Prospect): Promise<void> {
  try {
    const order: Order = await OrdersService.createOrder({
      product_type: 'website',
      prospect_id: prospect.id,
      business_name: prospect.name,
      customer_email: prospect.email ?? null,
    })
    toast.success(`Vente créée pour « ${prospect.name} »`)
    drawerStack.push({ kind: 'order', order, mode: 'view' })
    navigateTo('/dashboard/orders')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la création de la vente')
  }
}

/**
 * Contacted toggle from the prospect drawer — persist and broadcast.
 * @param prospect - The prospect whose contacted status was toggled.
 */
async function handleToggleContacted(prospect: Prospect): Promise<void> {
  const next: boolean = !prospect.contacted
  try {
    const updated: Prospect = await ProspectsService.updateProspect(prospect.id, { contacted: next })
    drawerStack.notifyProspectUpdated(updated)
    toast.success(next ? `« ${prospect.name} » marqué comme contacté` : `« ${prospect.name} » remis en non contacté`)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la mise à jour')
  }
}

/**
 * Convert an HTML email body to editable plain text (paragraph/line breaks
 * preserved, tags stripped).
 * @param html - HTML body from the email log (may be null).
 * @returns Plain-text version, or an empty string.
 */
function htmlToPlainText(html: string | null | undefined): string {
  if (!html) return ''
  const withBreaks: string = html.replace(/<br\s*\/?>/gi, '\n').replace(/<\/p>/gi, '\n\n')
  const doc: Document = new DOMParser().parseFromString(withBreaks, 'text/html')
  return (doc.body.textContent ?? '').replace(/\n{3,}/g, '\n\n').trim()
}

/** Stack the email composer prefilled from the log row (resend of a delivered email). */
function handleResendEmail(): void {
  const entry: EmailLogDrawerEntry | null = emailLogEntry.value
  if (!entry) return
  drawerStack.push({
    kind: 'send-email',
    prospect: null,
    prefill: {
      recipient_email: entry.log.recipient_email,
      recipient_name: entry.log.recipient_name ?? '',
      subject: entry.log.subject,
      body: htmlToPlainText(entry.log.body_html),
    },
  })
}

/** Open the resend sub-page (email-only form) for a failed email. */
function handleOpenResend(): void {
  const entry: EmailLogDrawerEntry | null = emailLogEntry.value
  if (!entry) return
  drawerStack.push({ kind: 'email-resend', log: entry.log })
}

/** Refresh the logs list after a resend, then return to the log view. */
function handleEmailResent(): void {
  drawerStack.bumpEmailLogsRefresh()
  if (drawerStack.hasPrevious) drawerStack.back()
}

/** Refresh logs after send; back or close the stack. */
function handleEmailSent(): void {
  drawerStack.bumpEmailLogsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/** Refresh the SMS history after send; back or close the stack. */
function handleSmsSent(): void {
  drawerStack.bumpSmsMessagesRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/**
 * « SMS » action — stack the composer on top of the prospect drawer.
 * @param prospect - The prospect used to prefill the composer.
 */
function handleSendSms(prospect: Prospect): void {
  drawerStack.push({ kind: 'send-sms', prospect })
}

/**
 * « Renvoyer » from an SMS log — open the composer prefilled from the sent SMS.
 * The mandatory STOP mention is stripped since the composer re-appends it.
 * @param message - The SMS to resend.
 */
function handleResendSms(message: SmsMessage): void {
  const text: string = message.body.replace(/\s*STOP au 36180\s*$/i, '').trim()
  drawerStack.push({
    kind: 'send-sms',
    prospect: null,
    prefill: { to: message.to_e164, recipient_name: message.recipient_name ?? '', text },
  })
}

/** Refresh templates after save; back or close the stack. */
function handleTemplateSaved(): void {
  drawerStack.bumpEmailTemplatesRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/**
 * Switch the template drawer from preview to edit (same kind → replaces top).
 * @param template - Template to edit.
 */
function handleTemplateEdit(template: EmailTemplate): void {
  drawerStack.push({ kind: 'email-template', mode: 'edit', template })
}

/**
 * Escape closes the top drawer (revealing the previous stacked one, if any).
 * Skips events already consumed (e.g. by the command palette).
 * @param event - Keyboard event.
 */
function handleKeydown(event: KeyboardEvent): void {
  if (event.key === 'Escape' && !event.defaultPrevented && drawerStack.topEntry) {
    drawerStack.back()
  }
}

/** Whether the prospect drawer sits on its edit form (browsing is disabled then). */
const isProspectEditing: ComputedRef<boolean> = computed(
  (): boolean => prospectEntry.value !== null && prospectDrawer.value?.editMode === true,
)

// A single gesture layer for the stack: swipe right pops the top drawer, swipe left steps to the next prospect.
useHorizontalSwipe((): EventTarget | null => (import.meta.client ? document.body : null), {
  enabled: (): boolean => isMobile.value && drawerStack.topEntry !== null,
  onSwipeRight: (): void => {
    if (isProspectEditing.value) return
    drawerStack.back()
  },
  onSwipeLeft: (): void => {
    if (prospectEntry.value !== null && !isProspectEditing.value && canBrowseNext.value) {
      browseToProspect('next')
    }
  },
})

// A URL hash marks an open drawer so a browser/OS back (iOS edge-swipe, Android) closes it, not the page.
const DRAWER_HISTORY_HASH: string = '#drawer'

/** Router used to add/remove the drawer history entry without re-navigating the page. */
const router: ReturnType<typeof useRouter> = useRouter()

/** Current route — watched to detect a back that strips the drawer hash. */
const route: ReturnType<typeof useRoute> = useRoute()

/** Whether any drawer is currently open. */
const isDrawerOpen: ComputedRef<boolean> = computed((): boolean => drawerStack.topEntry !== null)

// Opening pushes the hash entry (same route → no remount), closing from the app pops it back.
watch(isDrawerOpen, (open: boolean, wasOpen: boolean): void => {
  if (open && !wasOpen && route.hash !== DRAWER_HISTORY_HASH) {
    router.push({ path: route.path, query: route.query, hash: DRAWER_HISTORY_HASH })
  } else if (!open && wasOpen && route.hash === DRAWER_HISTORY_HASH) {
    router.back()
  }
})

watch(
  (): string => route.hash,
  (hash: string, previousHash: string): void => {
    // Back stripped the drawer hash while a drawer is open → close it, the page stays put.
    if (previousHash === DRAWER_HISTORY_HASH && hash !== DRAWER_HISTORY_HASH && drawerStack.topEntry !== null) {
      drawerStack.closeAll()
    }
  },
)

// Left-edge zone (px) where a touch would start iOS's back-swipe — blocked while a drawer is open.
const EDGE_BACK_GUARD_PX: number = 30

/**
 * Block iOS's edge back-swipe while a drawer is open so our own swipe closes it cleanly, without the native reset.
 * @param event - The native touch-start event.
 */
function preventEdgeBackSwipe(event: TouchEvent): void {
  if (drawerStack.topEntry === null) return
  const startX: number | undefined = event.touches[0]?.clientX
  if (startX !== undefined && startX <= EDGE_BACK_GUARD_PX) {
    event.preventDefault()
  }
}

onMounted((): void => {
  window.addEventListener('keydown', handleKeydown)
  document.addEventListener('touchstart', preventEdgeBackSwipe, { passive: false })
  // A drawer restored from sessionStorage on load has no hash yet — add one so back still closes it.
  if (drawerStack.topEntry !== null && route.hash !== DRAWER_HISTORY_HASH) {
    router.push({ path: route.path, query: route.query, hash: DRAWER_HISTORY_HASH })
  }
})

onBeforeUnmount((): void => {
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('touchstart', preventEdgeBackSwipe)
})
</script>
