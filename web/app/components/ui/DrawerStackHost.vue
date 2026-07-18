<template>
  <div>
    <!-- Prospect detail -->
    <UiProspectDrawer
      :open="prospectEntry !== null"
      :prospect="prospectEntry?.prospect ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @updated="handleProspectUpdated"
      @deleted="handleProspectDeleted"
      @add-to-campaign="handleAddToCampaign"
      @send-email="handleSendEmail"
      @mark-as-sold="handleMarkAsSold"
      @toggle-contacted="handleToggleContacted"
    />

    <!-- Manual email composer -->
    <UiSendEmailDrawer
      :open="sendEmailEntry !== null"
      :prospect="sendEmailEntry?.prospect ?? null"
      :prefill="sendEmailEntry?.prefill ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @sent="handleEmailSent"
    />

    <!-- Email log detail -->
    <UiEmailLogDrawer
      :open="emailLogEntry !== null"
      :log="emailLogEntry?.log ?? null"
      :campaign-name="emailLogEntry?.campaignName"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @resend="handleResendEmail"
    />

    <!-- Email template create / edit / preview -->
    <UiEmailTemplateDrawer
      :open="emailTemplateEntry !== null"
      :mode="emailTemplateEntry?.mode ?? 'create'"
      :template="emailTemplateEntry?.template ?? null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @saved="handleTemplateSaved"
      @edit="handleTemplateEdit"
    />

    <!-- User profile edit -->
    <UiProfileDrawer
      :open="profileEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Organization (team) management -->
    <UiOrganizationDrawer
      :open="organizationEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Presenter clip (prospection videos) -->
    <UiPresenterVideoDrawer
      :open="presenterVideoEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Campaign creation -->
    <UiCreateCampaignDrawer
      :open="createCampaignEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Manual prospect creation -->
    <UiAddProspectDrawer
      :open="addProspectEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
      @created="handleProspectCreated"
    />

    <!-- Prospect search (scraping) -->
    <UiSearchProspectsDrawer
      :open="searchProspectsEntry !== null"
      :show-back="hasPrevious"
      :prefill="searchProspectsEntry?.prefill ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Send policy (email cadence) -->
    <UiSendPolicyDrawer
      :open="sendPolicyEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Coverage map: filters & zones -->
    <UiCoverageFiltersDrawer
      :open="coverageFiltersEntry !== null"
      :show-back="hasPrevious"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />

    <!-- Coverage map: zone prospects -->
    <UiCoverageProspectsDrawer
      :open="coverageProspectsEntry !== null"
      :show-back="hasPrevious"
      :zone="coverageProspectsEntry?.zone ?? null"
      @close="drawerStack.closeAll()"
      @back="drawerStack.back()"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type {
  AddProspectDrawerEntry,
  CoverageFiltersDrawerEntry,
  CoverageProspectsDrawerEntry,
  CreateCampaignDrawerEntry,
  EmailLogDrawerEntry,
  EmailTemplateDrawerEntry,
  OrganizationDrawerEntry,
  PresenterVideoDrawerEntry,
  ProfileDrawerEntry,
  ProspectDrawerEntry,
  SearchProspectsDrawerEntry,
  SendEmailDrawerEntry,
  SendPolicyDrawerEntry,
} from '~/types/DrawerStack'
import type { EmailTemplate, Prospect } from '~/types'
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { updateProspect } from '~/services/prospectsService'
import { createOrder } from '~/services/ordersService'
import { useToast } from '~/composables/useToast'

const drawerStack = useDrawerStackStore()

const toast = useToast()

/** Top entry narrowed to the prospect drawer (null when another kind is on top). */
const prospectEntry: ComputedRef<ProspectDrawerEntry | null> = computed((): ProspectDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'prospect' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the send-email drawer. */
const sendEmailEntry: ComputedRef<SendEmailDrawerEntry | null> = computed((): SendEmailDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'send-email' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-log drawer. */
const emailLogEntry: ComputedRef<EmailLogDrawerEntry | null> = computed((): EmailLogDrawerEntry | null => {
  return drawerStack.topEntry?.kind === 'email-log' ? drawerStack.topEntry : null
})

/** Top entry narrowed to the email-template drawer. */
const emailTemplateEntry: ComputedRef<EmailTemplateDrawerEntry | null> = computed(
  (): EmailTemplateDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'email-template' ? drawerStack.topEntry : null
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

/** Top entry narrowed to the presenter clip drawer. */
const presenterVideoEntry: ComputedRef<PresenterVideoDrawerEntry | null> = computed(
  (): PresenterVideoDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'presenter-video' ? drawerStack.topEntry : null
  },
)

/** Top entry narrowed to the campaign creation drawer. */
const createCampaignEntry: ComputedRef<CreateCampaignDrawerEntry | null> = computed(
  (): CreateCampaignDrawerEntry | null => {
    return drawerStack.topEntry?.kind === 'create-campaign' ? drawerStack.topEntry : null
  },
)

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

/**
 * Prospect deleted from the drawer — close it and notify pages.
 * @param prospectId - Identifier of the deleted prospect.
 */
function handleProspectDeleted(prospectId: number): void {
  drawerStack.notifyProspectDeleted(prospectId)
}

/**
 * « Campagne » action — chain the prospect into the campaigns page. The
 * drawer stays open across the navigation (that's the whole point of the
 * persistent stack).
 * @param prospect - The prospect to add to a campaign.
 */
function handleAddToCampaign(prospect: Prospect): void {
  navigateTo(`/dashboard/campaigns?addProspect=${prospect.id}`)
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
    await createOrder({
      product_type: 'website',
      prospect_id: prospect.id,
      business_name: prospect.name,
      customer_email: prospect.email ?? null,
    })
    toast.success(`Vente créée pour « ${prospect.name} »`)
    drawerStack.closeAll()
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
    const updated: Prospect = await updateProspect(prospect.id, { contacted: next })
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

/**
 * « Renvoyer un email » from the log drawer — stack the composer prefilled
 * with the log's recipient, subject and body.
 */
function handleResendEmail(): void {
  const entry = emailLogEntry.value
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

/**
 * Email sent from the composer — refresh the logs and go back to the
 * previous drawer when one exists (e.g. the prospect), else close.
 */
function handleEmailSent(): void {
  drawerStack.bumpEmailLogsRefresh()
  if (drawerStack.hasPrevious) {
    drawerStack.back()
  } else {
    drawerStack.closeAll()
  }
}

/**
 * Template saved (created or edited) — refresh the templates page and go
 * back or close.
 */
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

onMounted((): void => {
  window.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount((): void => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>
