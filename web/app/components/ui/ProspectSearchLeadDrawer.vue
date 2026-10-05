<template>
  <Teleport to="body">
    <Transition name="drawer-panel">
      <div
        v-if="props.open && lead"
        class="fixed top-0 right-0 z-50 flex h-[calc(100dvh-var(--app-drawer-bottom))] w-full max-w-[460px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] pt-[env(safe-area-inset-top)] pb-[var(--app-drawer-bottom-padding)] shadow-2xl"
      >
        <UiDrawerHeader
          :title="lead.name"
          icon="i-lucide-store"
          :subtitle="store.buildTradeAndTownLabel(lead)"
          :show-back="props.showBack"
          @back="emit('back')"
          @close="emit('close')"
        >
          <template #badges>
            <div class="mb-1 flex flex-wrap items-center gap-1.5">
              <span class="app-label">Fiche du lead</span>
              <span :class="['app-badge', leadQuality.badgeClass]">{{ leadQuality.label }}</span>
            </div>
          </template>
        </UiDrawerHeader>

        <UiDrawerBrowseNav
          :position-label="browsePositionLabel"
          :can-previous="positionInBrowsedLeads > 0"
          :can-next="positionInBrowsedLeads >= 0 && positionInBrowsedLeads < browsedLeads.length - 1"
          @previous="browseToPosition(positionInBrowsedLeads - 1)"
          @next="browseToPosition(positionInBrowsedLeads + 1)"
        />

        <div class="flex-1 space-y-5 overflow-x-hidden overflow-y-auto px-5 py-4">
          <UiCallout v-if="lead.reject_detail" variant="warning">{{ lead.reject_detail }}</UiCallout>

          <section aria-labelledby="prospect-search-lead-contact-title">
            <h3 id="prospect-search-lead-contact-title" class="app-label mb-2">Coordonnées</h3>
            <dl
              class="divide-y divide-[var(--app-line-soft)] rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
            >
              <div
                v-for="detail in contactDetails"
                :key="detail.key"
                class="px-3 py-2"
                :class="detail.isLongValue ? '' : 'flex items-baseline justify-between gap-4'"
              >
                <dt class="shrink-0 text-xs text-[var(--app-ink-soft)]">{{ detail.label }}</dt>
                <dd class="min-w-0 text-xs" :class="detail.isLongValue ? 'mt-0.5' : 'text-right'">
                  <span class="font-medium break-words text-[var(--app-ink)]">{{ detail.value }}</span>
                  <span v-if="detail.note" class="mt-0.5 block text-[11px] text-[var(--app-ink-soft)]">
                    {{ detail.note }}
                  </span>
                </dd>
              </div>
            </dl>
            <p class="font-label mt-2 text-[11px] text-[var(--app-ink-soft)]">
              Trouvé via {{ PROSPECT_SEARCH_ORIGIN_LABELS[lead.origin] }} · {{ formatRelativeTime(lead.created_at) }}
            </p>
          </section>

          <section aria-labelledby="prospect-search-lead-criteria-title">
            <h3 id="prospect-search-lead-criteria-title" class="app-label mb-2">Critères</h3>
            <ProspectSearchLeadCriteria :candidate="lead" should-show-labels />
          </section>

          <section v-if="leadLinks.length > 0" aria-labelledby="prospect-search-lead-links-title">
            <h3 id="prospect-search-lead-links-title" class="app-label mb-2">Liens</h3>
            <ul class="flex flex-wrap items-center gap-2">
              <li v-for="link in leadLinks" :key="link.key" class="inline-flex items-center gap-1.5">
                <a
                  :href="link.href"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="app-btn-secondary h-8 min-h-8 px-3 text-xs"
                >
                  <UIcon :name="link.icon" class="h-3.5 w-3.5 shrink-0" />
                  {{ link.label }}
                  <UIcon name="i-lucide-external-link" class="h-3 w-3 shrink-0 opacity-60" />
                </a>
                <span v-if="link.warning" :class="['app-badge', link.warning.badgeClass]">
                  {{ link.warning.label }}
                </span>
              </li>
            </ul>
          </section>

          <section v-if="lead.evidence.length > 0" aria-labelledby="prospect-search-lead-evidence-title">
            <h3 id="prospect-search-lead-evidence-title" class="app-label mb-2">
              Preuves <span class="tracking-normal normal-case">({{ lead.evidence.length }})</span>
            </h3>
            <ProspectSearchEvidenceList :evidence="lead.evidence" />
          </section>
        </div>

        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button
            type="button"
            class="app-btn-secondary flex-1"
            :disabled="isSendingDecision"
            @click="decisions.rejectLead(lead)"
          >
            <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
            Refuser
          </button>
          <button
            type="button"
            class="app-btn-primary flex-1"
            :disabled="isSendingDecision"
            @click="decisions.acceptLead(lead)"
          >
            <UIcon
              :name="isSendingDecision ? 'i-lucide-loader-circle' : 'i-lucide-check'"
              :class="['h-3.5 w-3.5', isSendingDecision && 'animate-spin']"
            />
            Accepter
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType } from 'vue'
import type { UseProspectSearchDecisionsReturn } from '~/types/Composables'
import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import type { StatusPresentation } from '~/types/StatusPresentation'
import type {
  ProspectSearchLeadContactDetail,
  ProspectSearchLeadLink,
  UiProspectSearchLeadDrawerEmits,
  UiProspectSearchLeadDrawerProps,
} from '~/types/UiProspectSearchLeadDrawer'
import { computed, watch } from 'vue'
import { useProspectSearchDecisions } from '~/composables/useProspectSearchDecisions'
import {
  PROSPECT_SEARCH_EMAIL_PROOF_LABELS,
  PROSPECT_SEARCH_ORIGIN_LABELS,
  PROSPECT_SEARCH_WEBSITE_WARNINGS,
} from '~/constants/prospectSearch'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useProspectSearchStore } from '~/stores/prospectSearch'
import { formatRelativeTime } from '~/utils/date'
import { ProspectSearches } from '~/utils/prospectSearches'

/** One lead waiting for a decision; once it is decided, here or elsewhere, the drawer shows the next one of its list. */
const props: UiProspectSearchLeadDrawerProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  candidate: {
    type: Object as PropType<ProspectSearchCandidate | null>,
    default: null,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<UiProspectSearchLeadDrawerEmits> = defineEmits<UiProspectSearchLeadDrawerEmits>()

const store: ReturnType<typeof useProspectSearchStore> = useProspectSearchStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const decisions: UseProspectSearchDecisionsReturn = useProspectSearchDecisions()

let lastPositionInBrowsedLeads: number = 0

const lead: ComputedRef<ProspectSearchCandidate | null> = computed((): ProspectSearchCandidate | null => {
  const openedLead: ProspectSearchCandidate | null = props.candidate ?? null
  if (openedLead === null) return null
  const refreshedLead: ProspectSearchCandidate | undefined = store.pendingCandidates.find(
    (candidate: ProspectSearchCandidate): boolean => candidate.id === openedLead.id,
  )
  return refreshedLead ?? openedLead
})

const isLeadStillWaiting: ComputedRef<boolean> = computed((): boolean => {
  const openedLeadId: number | undefined = props.candidate?.id
  if (openedLeadId === undefined || !store.hasLoadedPendingCandidates) return true
  return store.pendingCandidates.some((candidate: ProspectSearchCandidate): boolean => candidate.id === openedLeadId)
})

const isSendingDecision: ComputedRef<boolean> = computed(
  (): boolean => lead.value !== null && store.busyCandidateIds.includes(lead.value.id),
)

const leadQuality: ComputedRef<StatusPresentation> = computed(
  (): StatusPresentation => (lead.value ? ProspectSearches.leadQuality(lead.value) : { label: '', badgeClass: '' }),
)

const browsedLeads: ComputedRef<ProspectSearchCandidate[]> = computed((): ProspectSearchCandidate[] => {
  if (store.leadBrowseIds.length === 0) return store.pendingCandidates
  const stillWaitingLeads: ProspectSearchCandidate[] = []
  for (const browsedId of store.leadBrowseIds) {
    const stillWaitingLead: ProspectSearchCandidate | undefined = store.pendingCandidates.find(
      (candidate: ProspectSearchCandidate): boolean => candidate.id === browsedId,
    )
    if (stillWaitingLead) stillWaitingLeads.push(stillWaitingLead)
  }
  return stillWaitingLeads
})

const positionInBrowsedLeads: ComputedRef<number> = computed((): number => {
  const openedLeadId: number | undefined = props.candidate?.id
  return browsedLeads.value.findIndex((candidate: ProspectSearchCandidate): boolean => candidate.id === openedLeadId)
})

const browsePositionLabel: ComputedRef<string> = computed((): string => {
  const hasNeighbour: boolean = positionInBrowsedLeads.value >= 0 && browsedLeads.value.length > 1
  return hasNeighbour ? `${positionInBrowsedLeads.value + 1} / ${browsedLeads.value.length}` : ''
})

const contactDetails: ComputedRef<ProspectSearchLeadContactDetail[]> = computed(
  (): ProspectSearchLeadContactDetail[] => {
    const openedLead: ProspectSearchCandidate | null = lead.value
    if (openedLead === null) return []
    const details: ProspectSearchLeadContactDetail[] = [buildPhoneDetail(openedLead), buildEmailDetail(openedLead)]
    if (openedLead.address) {
      details.push({ key: 'address', label: 'Adresse', value: openedLead.address, note: null, isLongValue: true })
    }
    if (openedLead.google_rating !== null) {
      const reviewCount: number | null = openedLead.google_reviews_count
      details.push({
        key: 'rating',
        label: 'Note Google',
        value: ProspectSearches.ratingLabel(openedLead.google_rating),
        note: reviewCount === null ? null : `${reviewCount.toLocaleString('fr-FR')} avis`,
        isLongValue: false,
      })
    }
    if (openedLead.google_category) {
      details.push({
        key: 'category',
        label: 'Catégorie Google',
        value: openedLead.google_category,
        note: null,
        isLongValue: false,
      })
    }
    if (openedLead.owner_name) {
      details.push({ key: 'owner', label: 'Dirigeant', value: openedLead.owner_name, note: null, isLongValue: false })
    }
    if (openedLead.registry_number) {
      details.push({
        key: 'registry',
        label: 'Registre',
        value: openedLead.registry_number,
        note: null,
        isLongValue: false,
      })
    }
    return details
  },
)

const leadLinks: ComputedRef<ProspectSearchLeadLink[]> = computed((): ProspectSearchLeadLink[] => {
  const openedLead: ProspectSearchCandidate | null = lead.value
  if (openedLead === null) return []
  const googleHref: string | null = ProspectSearches.externalHref(openedLead.google_maps_url)
  const facebookHref: string | null = ProspectSearches.externalHref(openedLead.facebook_url)
  const websiteHref: string | null = ProspectSearches.externalHref(openedLead.website)
  const links: ProspectSearchLeadLink[] = []
  if (googleHref) {
    links.push({ key: 'google', label: 'Fiche Google', href: googleHref, icon: 'i-lucide-map-pin', warning: null })
  }
  if (facebookHref) {
    links.push({
      key: 'facebook',
      label: 'Page Facebook',
      href: facebookHref,
      icon: 'i-lucide-facebook',
      warning: null,
    })
  }
  if (websiteHref) {
    links.push({
      key: 'website',
      label: 'Site web',
      href: websiteHref,
      icon: 'i-lucide-globe',
      warning: PROSPECT_SEARCH_WEBSITE_WARNINGS[openedLead.website_status ?? ''] ?? null,
    })
  }
  return links
})

/**
 * Describe the phone number of a lead, and whether it is a mobile or a landline.
 * @param openedLead - The lead shown.
 * @returns The phone line of the contact card, with a dash when no number was found.
 */
function buildPhoneDetail(openedLead: ProspectSearchCandidate): ProspectSearchLeadContactDetail {
  if (!openedLead.phone) return { key: 'phone', label: 'Téléphone', value: '—', note: null, isLongValue: false }
  return {
    key: 'phone',
    label: 'Téléphone',
    value: openedLead.phone,
    note: openedLead.phone_is_mobile ? 'portable' : 'ligne fixe',
    isLongValue: false,
  }
}

/**
 * Describe the email of a lead, and how it is proven.
 * @param openedLead - The lead shown.
 * @returns The email line of the contact card, with a dash when no address was found.
 */
function buildEmailDetail(openedLead: ProspectSearchCandidate): ProspectSearchLeadContactDetail {
  if (!openedLead.email) return { key: 'email', label: 'Email', value: '—', note: null, isLongValue: false }
  return {
    key: 'email',
    label: 'Email',
    value: openedLead.email,
    note: openedLead.email_proof_level ? PROSPECT_SEARCH_EMAIL_PROOF_LABELS[openedLead.email_proof_level] : null,
    isLongValue: true,
  }
}

/**
 * Show another lead of the browsed list, keeping the drawer in place.
 * @param position - Position of the lead to show.
 */
function browseToPosition(position: number): void {
  const leadToShow: ProspectSearchCandidate | undefined = browsedLeads.value[position]
  if (leadToShow) drawerStack.push({ kind: 'prospect-search-lead', candidate: leadToShow })
}

watch(
  positionInBrowsedLeads,
  (position: number): void => {
    if (position >= 0) lastPositionInBrowsedLeads = position
  },
  { immediate: true },
)

watch(isLeadStillWaiting, (isStillWaiting: boolean): void => {
  if (isStillWaiting || !props.open) return
  const nextLead: ProspectSearchCandidate | undefined =
    browsedLeads.value[lastPositionInBrowsedLeads] ?? browsedLeads.value[lastPositionInBrowsedLeads - 1]
  if (nextLead) {
    drawerStack.push({ kind: 'prospect-search-lead', candidate: nextLead })
    return
  }
  if (props.showBack) emit('back')
  else emit('close')
})
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
