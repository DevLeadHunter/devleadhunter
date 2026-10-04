<template>
  <article class="px-4 py-3.5 @2xl:px-5">
    <div class="flex flex-col gap-3 @3xl:flex-row @3xl:items-start @3xl:justify-between">
      <div class="min-w-0 flex-1">
        <div class="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
          <h3 class="min-w-0 text-sm font-semibold break-words text-[var(--app-ink)]">{{ props.candidate.name }}</h3>
          <span class="font-label text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase">
            {{ PROSPECT_SEARCH_ORIGIN_LABELS[props.candidate.origin] }}
          </span>
        </div>
        <p class="mt-0.5 text-xs text-[var(--app-ink-soft)]">{{ tradeAndTown }}</p>
        <p
          v-if="props.candidate.reject_detail"
          class="mt-1.5 text-xs leading-relaxed break-words text-[var(--app-ink)]"
        >
          {{ props.candidate.reject_detail }}
        </p>

        <ul
          v-if="hasContactFacts"
          class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-[var(--app-ink-soft)]"
        >
          <li v-if="props.candidate.phone" class="inline-flex items-center gap-1.5">
            <UIcon name="i-lucide-phone" class="h-3.5 w-3.5 shrink-0" />
            <span class="text-[var(--app-ink)] tabular-nums">{{ props.candidate.phone }}</span>
            <span v-if="props.candidate.phone_is_mobile" class="app-badge">portable</span>
          </li>
          <li v-if="props.candidate.email" class="inline-flex min-w-0 flex-wrap items-center gap-1.5">
            <UIcon name="i-lucide-mail" class="h-3.5 w-3.5 shrink-0" />
            <span class="min-w-0 break-all text-[var(--app-ink)]">{{ props.candidate.email }}</span>
            <span v-if="emailProof" :class="['app-badge', emailProof.badgeClass]">{{ emailProof.label }}</span>
          </li>
          <li v-if="googleRatingLabel" class="inline-flex items-center gap-1.5">
            <UIcon name="i-lucide-star" class="h-3.5 w-3.5 shrink-0" />
            <span class="text-[var(--app-ink)] tabular-nums">{{ googleRatingLabel }}</span>
          </li>
          <li v-if="props.candidate.owner_name" class="inline-flex min-w-0 items-center gap-1.5">
            <UIcon name="i-lucide-user-round" class="h-3.5 w-3.5 shrink-0" />
            Dirigeant :
            <span class="min-w-0 break-words text-[var(--app-ink)]">{{ props.candidate.owner_name }}</span>
          </li>
          <li v-if="props.candidate.registry_number" class="inline-flex min-w-0 items-center gap-1.5">
            <UIcon name="i-lucide-badge-check" class="h-3.5 w-3.5 shrink-0" />
            Registre :
            <span class="min-w-0 break-all text-[var(--app-ink)] tabular-nums">{{
              props.candidate.registry_number
            }}</span>
          </li>
        </ul>

        <div
          v-if="links.length > 0 || props.candidate.evidence.length > 0"
          class="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-0.5 text-xs"
        >
          <span v-for="link in links" :key="link.key" class="inline-flex items-center gap-1.5">
            <a
              :href="link.href"
              target="_blank"
              rel="noopener noreferrer"
              class="inline-flex min-h-7 items-center gap-1 font-medium text-[var(--app-ink)] underline underline-offset-2 transition-opacity hover:opacity-70"
            >
              <UIcon :name="link.icon" class="h-3.5 w-3.5 shrink-0" />
              {{ link.label }}
            </a>
            <span v-if="link.warning" :class="['app-badge', link.warning.badgeClass]">{{ link.warning.label }}</span>
          </span>
          <button
            v-if="props.candidate.evidence.length > 0"
            type="button"
            class="inline-flex min-h-7 cursor-pointer items-center gap-1 font-medium text-[var(--app-ink-soft)] transition-colors hover:text-[var(--app-ink)]"
            :aria-expanded="isShowingEvidence"
            @click="isShowingEvidence = !isShowingEvidence"
          >
            <UIcon name="i-lucide-file-search" class="h-3.5 w-3.5 shrink-0" />
            {{ isShowingEvidence ? 'Masquer les preuves' : `Voir les preuves (${props.candidate.evidence.length})` }}
            <UIcon
              name="i-lucide-chevron-down"
              :class="['h-3.5 w-3.5 shrink-0 transition-transform', isShowingEvidence && 'rotate-180']"
            />
          </button>
        </div>
      </div>

      <div v-if="canOpenProspect || canDecide || canKeepAnyway" class="flex shrink-0 flex-wrap items-center gap-2">
        <button
          v-if="canDecide"
          type="button"
          class="app-btn-primary h-11 min-h-11 flex-1 px-3 text-xs @md:flex-none @3xl:h-8 @3xl:min-h-8"
          :disabled="props.isBusy"
          @click="emit('keep', props.candidate.id)"
        >
          <UIcon
            :name="props.isBusy ? 'i-lucide-loader-circle' : 'i-lucide-check'"
            :class="['h-3.5 w-3.5', props.isBusy && 'animate-spin']"
          />
          Garder
        </button>
        <button
          v-if="canDecide"
          type="button"
          class="app-btn-secondary h-11 min-h-11 flex-1 px-3 text-xs @md:flex-none @3xl:h-8 @3xl:min-h-8"
          :disabled="props.isBusy"
          @click="emit('reject', props.candidate.id)"
        >
          Écarter
        </button>
        <button
          v-if="canKeepAnyway"
          type="button"
          class="app-btn-secondary h-11 min-h-11 flex-1 px-3 text-xs @md:flex-none @3xl:h-8 @3xl:min-h-8"
          :disabled="props.isBusy"
          @click="emit('keep', props.candidate.id)"
        >
          <UIcon v-if="props.isBusy" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
          Garder quand même
        </button>
        <button
          v-if="canOpenProspect"
          type="button"
          class="app-btn-secondary h-11 min-h-11 flex-1 px-3 text-xs @md:flex-none @3xl:h-8 @3xl:min-h-8"
          :disabled="props.isOpeningProspect"
          @click="openProspect"
        >
          Ouvrir la fiche
          <UIcon
            :name="props.isOpeningProspect ? 'i-lucide-loader-circle' : 'i-lucide-chevron-right'"
            :class="['h-3.5 w-3.5', props.isOpeningProspect && 'animate-spin']"
          />
        </button>
      </div>
    </div>

    <ProspectSearchEvidenceList v-if="isShowingEvidence" :evidence="props.candidate.evidence" class="mt-3" />
  </article>
</template>

<script lang="ts" setup>
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { ProspectSearchCandidate } from '~/types/ProspectSearch'
import type {
  ProspectSearchCandidateLink,
  ProspectSearchCandidateRowEmits,
  ProspectSearchCandidateRowProps,
} from '~/types/ProspectSearchCandidateRow'
import type { StatusPresentation } from '~/types/StatusPresentation'
import { computed, ref } from 'vue'
import {
  PROSPECT_SEARCH_EMAIL_PROOF_PRESENTATION,
  PROSPECT_SEARCH_KNOWN_BUSINESS_REASONS,
  PROSPECT_SEARCH_ORIGIN_LABELS,
} from '~/constants/prospectSearch'
import { ProspectSearches } from '~/utils/prospectSearches'

/** One business a search looked at: what was found, the proofs behind it, and the decision left to the user. */
const props: ProspectSearchCandidateRowProps = defineProps({
  candidate: {
    type: Object as PropType<ProspectSearchCandidate>,
    required: true,
  },
  tradeLabel: {
    type: String,
    required: true,
  },
  isBusy: {
    type: Boolean,
    required: true,
  },
  isOpeningProspect: {
    type: Boolean,
    required: true,
  },
})

const emit: EmitFn<ProspectSearchCandidateRowEmits> = defineEmits<ProspectSearchCandidateRowEmits>()

const WEBSITE_WARNINGS: Record<string, StatusPresentation> = {
  dead: { label: 'site en panne', badgeClass: 'app-badge--danger' },
  placeholder: { label: 'mini-site annuaire', badgeClass: '' },
}

const isShowingEvidence: Ref<boolean> = ref(false)

const tradeAndTown: ComputedRef<string> = computed((): string =>
  [props.tradeLabel, props.candidate.city ?? props.candidate.searched_city]
    .filter((part: string | null): part is string => Boolean(part))
    .join(' · '),
)

const emailProof: ComputedRef<StatusPresentation | null> = computed((): StatusPresentation | null =>
  props.candidate.email_proof_level
    ? PROSPECT_SEARCH_EMAIL_PROOF_PRESENTATION[props.candidate.email_proof_level]
    : null,
)

const googleRatingLabel: ComputedRef<string | null> = computed((): string | null => {
  const rating: number | null = props.candidate.google_rating
  if (rating === null) return null
  const formattedRating: string = ProspectSearches.ratingLabel(rating)
  const reviewCount: number | null = props.candidate.google_reviews_count
  return reviewCount === null ? formattedRating : `${formattedRating} · ${reviewCount.toLocaleString('fr-FR')} avis`
})

const hasContactFacts: ComputedRef<boolean> = computed((): boolean =>
  Boolean(
    props.candidate.phone ||
    props.candidate.email ||
    googleRatingLabel.value ||
    props.candidate.owner_name ||
    props.candidate.registry_number,
  ),
)

const links: ComputedRef<ProspectSearchCandidateLink[]> = computed((): ProspectSearchCandidateLink[] => {
  const googleHref: string | null = ProspectSearches.externalHref(props.candidate.google_maps_url)
  const facebookHref: string | null = ProspectSearches.externalHref(props.candidate.facebook_url)
  const websiteHref: string | null = ProspectSearches.externalHref(props.candidate.website)
  const candidateLinks: ProspectSearchCandidateLink[] = []
  if (googleHref) {
    candidateLinks.push({
      key: 'google',
      label: 'Fiche Google',
      href: googleHref,
      icon: 'i-lucide-map-pin',
      warning: null,
    })
  }
  if (facebookHref) {
    candidateLinks.push({
      key: 'facebook',
      label: 'Page Facebook',
      href: facebookHref,
      icon: 'i-lucide-facebook',
      warning: null,
    })
  }
  if (websiteHref) {
    candidateLinks.push({
      key: 'website',
      label: 'Site',
      href: websiteHref,
      icon: 'i-lucide-globe',
      warning: WEBSITE_WARNINGS[props.candidate.website_status ?? ''] ?? null,
    })
  }
  return candidateLinks
})

const canOpenProspect: ComputedRef<boolean> = computed((): boolean => props.candidate.prospect_id !== null)

const canDecide: ComputedRef<boolean> = computed(
  (): boolean =>
    props.candidate.status === 'to_confirm' ||
    props.candidate.status === 'needs_browser' ||
    props.candidate.status === 'discovered',
)

const canKeepAnyway: ComputedRef<boolean> = computed(
  (): boolean =>
    props.candidate.status === 'rejected' &&
    (props.candidate.reject_reason === null ||
      !PROSPECT_SEARCH_KNOWN_BUSINESS_REASONS.includes(props.candidate.reject_reason)),
)

/** Ask for the record of the prospect this candidate became, or already was. */
function openProspect(): void {
  if (props.candidate.prospect_id !== null) emit('open-prospect', props.candidate.prospect_id)
}
</script>
