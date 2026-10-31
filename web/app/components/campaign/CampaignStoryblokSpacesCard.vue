<template>
  <section
    v-if="hasSpaces || (!spacesSummary && loadErrorMessage)"
    class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5"
    aria-labelledby="campaign-storyblok-spaces-title"
  >
    <div class="mb-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-archive" class="h-4 w-4 text-[var(--app-ink)]" />
        <h3 id="campaign-storyblok-spaces-title" class="text-sm font-semibold text-[var(--app-ink)]">
          Espaces Storyblok
        </h3>
      </div>
      <p v-if="accountUsageLabel" class="text-xs text-[var(--app-ink-soft)]">{{ accountUsageLabel }}</p>
    </div>

    <p v-if="loadErrorMessage" class="mb-3 flex flex-wrap items-center gap-x-2 text-xs text-[var(--app-red)]">
      {{ loadErrorMessage }}
      <button
        type="button"
        class="cursor-pointer font-medium underline underline-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="isLoadingSummary"
        @click="loadSpacesSummary"
      >
        Réessayer
      </button>
    </p>

    <template v-if="spacesSummary">
      <p class="mb-3 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        Un espace ne sert qu'à filmer la vidéo et à vendre. En libérer un fait de la place : la démo reste en ligne
        exactement comme avant, et l'espace se recrée en un clic depuis la fiche du site. Les espaces des prospects qui
        ont regardé leur démo, répondu ou été invités sont gardés.
      </p>

      <ul
        class="divide-y divide-[var(--app-line)] rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
        aria-label="Espaces de la campagne"
      >
        <li v-if="spacesSummary.releasable.length > 0">
          <details class="group">
            <summary
              class="flex cursor-pointer list-none items-center gap-2.5 px-3 py-2.5 text-sm text-[var(--app-ink)] select-none [&::-webkit-details-marker]:hidden"
            >
              <UIcon name="i-lucide-circle-check" class="h-4 w-4 shrink-0 text-[var(--app-green)]" />
              <span class="min-w-0 flex-1">{{ releasableLabel }}</span>
              <UIcon
                name="i-lucide-chevron-down"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)] transition-transform group-open:rotate-180"
              />
            </summary>
            <ul class="space-y-1 px-3 pb-3 pl-9.5">
              <li v-for="site in spacesSummary.releasable" :key="site.demo_site_id">
                <NuxtLink
                  :to="`/dashboard/demo-sites/${site.demo_site_id}`"
                  class="text-xs text-[var(--app-ink-soft)] underline-offset-2 transition-colors hover:text-[var(--app-ink)] hover:underline"
                >
                  {{ site.business_name }}
                </NuxtLink>
              </li>
            </ul>
          </details>
        </li>
        <li v-for="group in keptGroups" :key="group.reason">
          <details class="group">
            <summary
              class="flex cursor-pointer list-none items-center gap-2.5 px-3 py-2.5 text-sm text-[var(--app-ink)] select-none [&::-webkit-details-marker]:hidden"
            >
              <UIcon name="i-lucide-lock" class="h-4 w-4 shrink-0 text-[var(--app-ink-soft)]" />
              <span class="min-w-0 flex-1">{{ keptGroupLabel(group) }}</span>
              <UIcon
                name="i-lucide-chevron-down"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)] transition-transform group-open:rotate-180"
              />
            </summary>
            <ul class="space-y-1 px-3 pb-3 pl-9.5">
              <li v-for="site in group.sites" :key="site.demo_site_id">
                <NuxtLink
                  :to="`/dashboard/demo-sites/${site.demo_site_id}`"
                  class="text-xs text-[var(--app-ink-soft)] underline-offset-2 transition-colors hover:text-[var(--app-ink)] hover:underline"
                >
                  {{ site.business_name }}
                </NuxtLink>
              </li>
            </ul>
          </details>
        </li>
      </ul>

      <div class="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="app-btn-secondary h-8 px-3 text-xs"
          :disabled="spacesSummary.releasable.length === 0 || isReleasing"
          @click="releaseConfirmModal?.open()"
        >
          <UIcon name="i-lucide-archive" class="h-3.5 w-3.5" />
          {{ releaseButtonLabel }}
        </button>
        <p v-if="isReleasing" class="text-xs text-[var(--app-ink-soft)]" role="status">
          {{ releaseProgressLabel }}
        </p>
      </div>

      <details
        v-if="lastReleaseFailures.length > 0"
        class="group mt-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
      >
        <summary
          class="text-muted flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-xs font-medium select-none hover:text-[var(--app-ink)] [&::-webkit-details-marker]:hidden"
        >
          <span class="flex items-center gap-2">
            <UIcon name="i-lucide-circle-slash" class="h-3.5 w-3.5 shrink-0" />
            {{ lastReleaseFailuresLabel }}
          </span>
          <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 shrink-0 transition-transform group-open:rotate-180" />
        </summary>
        <ul class="space-y-1.5 border-t border-[var(--app-line)] px-3 py-3">
          <li v-for="failure in lastReleaseFailures" :key="failure.site.demo_site_id" class="text-xs leading-relaxed">
            <NuxtLink
              :to="`/dashboard/demo-sites/${failure.site.demo_site_id}`"
              class="font-medium text-[var(--app-ink)] underline-offset-2 hover:underline"
            >
              {{ failure.site.business_name }}
            </NuxtLink>
            <span class="text-[var(--app-ink-soft)]"> : {{ failure.reason }}</span>
          </li>
        </ul>
      </details>
    </template>

    <UiConfirmModal
      ref="releaseConfirmModal"
      title="Libérer les espaces Storyblok"
      :message="releaseConfirmMessage"
      confirm-text="Libérer"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="releaseSpaces"
    />
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { UseToastReturn } from '~/types/Composables'
import type {
  CampaignStoryblokKeptSpace,
  CampaignStoryblokSpaceSite,
  CampaignStoryblokSpacesResponse,
} from '~/types/CampaignStoryblokSpaces'
import type {
  CampaignStoryblokKeptGroup,
  CampaignStoryblokReleaseFailure,
  CampaignStoryblokReleaseOutcome,
  CampaignStoryblokSpacesCardProps,
} from '~/types/CampaignStoryblokSpacesCard'
import type { UiConfirmModalHandle } from '~/types/UiConfirmModal'
import { computed, onMounted, ref, watch } from 'vue'
import { runBoundedGeocoding } from '~/composables/useFranceGeo'
import { useToast } from '~/composables/useToast'
import { CampaignService } from '~/services/campaignService'
import { DemoSiteService } from '~/services/demoSiteService'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'

/** The Storyblok spaces of the campaign's demo sites, with the button that releases those nobody still needs. */
const props: CampaignStoryblokSpacesCardProps = defineProps({
  campaignId: {
    type: Number,
    required: true,
  },
})

const toast: UseToastReturn = useToast()

const RELEASE_PARALLEL_REQUESTS: number = 3

const spacesSummary: Ref<CampaignStoryblokSpacesResponse | null> = ref(null)
const loadErrorMessage: Ref<string> = ref('')
const isLoadingSummary: Ref<boolean> = ref(false)
const isReleasing: Ref<boolean> = ref(false)
const releasedOrFailedCount: Ref<number> = ref(0)
const releaseTargetCount: Ref<number> = ref(0)
const lastReleaseFailures: Ref<CampaignStoryblokReleaseFailure[]> = ref([])
const releaseConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

let latestSummaryLoadNumber: number = 0

const hasSpaces: ComputedRef<boolean> = computed((): boolean => {
  const summary: CampaignStoryblokSpacesResponse | null = spacesSummary.value
  return summary !== null && summary.releasable.length + summary.kept.length > 0
})

const accountUsageLabel: ComputedRef<string> = computed((): string => {
  const summary: CampaignStoryblokSpacesResponse | null = spacesSummary.value
  if (!summary || summary.account_space_count === null) {
    return ''
  }
  return `${summary.account_space_count} espaces sur ${summary.account_space_limit} au compte Storyblok`
})

const releasableLabel: ComputedRef<string> = computed((): string =>
  CampaignResultsFormat.count(
    spacesSummary.value?.releasable.length ?? 0,
    'espace à libérer (prospect silencieux ou ayant refusé)',
    'espaces à libérer (prospects silencieux ou ayant refusé)',
  ),
)

const keptGroups: ComputedRef<CampaignStoryblokKeptGroup[]> = computed((): CampaignStoryblokKeptGroup[] => {
  const groups: Map<string, CampaignStoryblokKeptSpace[]> = new Map()
  for (const site of spacesSummary.value?.kept ?? []) {
    groups.set(site.reason, [...(groups.get(site.reason) ?? []), site])
  }
  return Array.from(
    groups,
    ([reason, sites]: [string, CampaignStoryblokKeptSpace[]]): CampaignStoryblokKeptGroup => ({
      reason,
      sites,
    }),
  )
})

const releaseButtonLabel: ComputedRef<string> = computed((): string => {
  const releasableCount: number = spacesSummary.value?.releasable.length ?? 0
  if (isReleasing.value) {
    return 'Libération…'
  }
  return releasableCount > 0
    ? `Libérer ${CampaignResultsFormat.count(releasableCount, 'espace', 'espaces')}`
    : 'Aucun espace à libérer'
})

const releaseProgressLabel: ComputedRef<string> = computed(
  (): string => `${releasedOrFailedCount.value} sur ${releaseTargetCount.value}`,
)

const releaseConfirmMessage: ComputedRef<string> = computed(
  (): string =>
    `Libérer ${CampaignResultsFormat.count(spacesSummary.value?.releasable.length ?? 0, 'espace', 'espaces')} Storyblok ? ` +
    "Chaque démo reste en ligne exactement comme avant : ses photos sont d'abord copiées chez nous. " +
    'Un espace se recrée en un clic depuis la fiche du site. Les espaces des prospects qui ont regardé leur démo, répondu ou été invités sont gardés.',
)

const lastReleaseFailuresLabel: ComputedRef<string> = computed((): string =>
  CampaignResultsFormat.count(
    lastReleaseFailures.value.length,
    "espace qui n'a pas pu être libéré",
    "espaces qui n'ont pas pu être libérés",
  ),
)

/**
 * The label of a group of spaces kept for the same reason.
 * @param group - The kept spaces and their reason.
 * @returns The count and the reason.
 */
function keptGroupLabel(group: CampaignStoryblokKeptGroup): string {
  return `${CampaignResultsFormat.count(group.sites.length, 'espace gardé', 'espaces gardés')} : ${group.reason}`
}

/**
 * Read which of the campaign's spaces a release takes and which stay.
 * @returns A promise resolved once the split is shown, or the failure is.
 */
async function loadSpacesSummary(): Promise<void> {
  latestSummaryLoadNumber += 1
  const loadNumber: number = latestSummaryLoadNumber
  isLoadingSummary.value = true
  try {
    const summary: CampaignStoryblokSpacesResponse = await CampaignService.getStoryblokSpaces(props.campaignId)
    if (loadNumber === latestSummaryLoadNumber) {
      spacesSummary.value = summary
      loadErrorMessage.value = ''
    }
  } catch {
    if (loadNumber === latestSummaryLoadNumber) {
      loadErrorMessage.value = "Les espaces Storyblok n'ont pas pu être lus."
    }
  } finally {
    if (loadNumber === latestSummaryLoadNumber) {
      isLoadingSummary.value = false
    }
  }
}

/**
 * Release one site's space, noting the success or the failure.
 * @param site - The site whose space is released.
 * @param outcome - What the release of all the sites has produced so far.
 * @returns A promise resolved once the site was tried; it never rejects.
 */
async function releaseOneSite(
  site: CampaignStoryblokSpaceSite,
  outcome: CampaignStoryblokReleaseOutcome,
): Promise<void> {
  try {
    await DemoSiteService.releaseDemoSiteStoryblokSpace(site.demo_site_id)
    outcome.releasedCount += 1
  } catch (error: unknown) {
    outcome.failures.push({
      site,
      reason: error instanceof Error && error.message ? error.message : "Storyblok n'a pas répondu.",
    })
  }
  releasedOrFailedCount.value += 1
}

/**
 * Release the releasable spaces three at a time, each one copying its photos before it is deleted.
 * @returns A promise resolved once every space was tried and the split re-read.
 */
async function releaseSpaces(): Promise<void> {
  const summary: CampaignStoryblokSpacesResponse | null = spacesSummary.value
  if (!summary || summary.releasable.length === 0 || isReleasing.value) {
    return
  }

  const waitingSites: CampaignStoryblokSpaceSite[] = [...summary.releasable]
  const outcome: CampaignStoryblokReleaseOutcome = { releasedCount: 0, failures: [] }
  isReleasing.value = true
  releasedOrFailedCount.value = 0
  releaseTargetCount.value = waitingSites.length
  lastReleaseFailures.value = []

  try {
    await runBoundedGeocoding(
      waitingSites,
      (site: CampaignStoryblokSpaceSite): Promise<void> => releaseOneSite(site, outcome),
      RELEASE_PARALLEL_REQUESTS,
    )
    lastReleaseFailures.value = outcome.failures
    if (outcome.releasedCount > 0) {
      toast.success(
        `${CampaignResultsFormat.count(outcome.releasedCount, 'espace libéré', 'espaces libérés')}, les démos restent en ligne.`,
      )
    }
    if (outcome.failures.length > 0) {
      toast.error(`${lastReleaseFailuresLabel.value}, voir le détail.`)
    }
  } finally {
    isReleasing.value = false
    await loadSpacesSummary()
  }
}

watch(
  (): number => props.campaignId,
  (): void => {
    loadSpacesSummary()
  },
)

onMounted((): void => {
  loadSpacesSummary()
})
</script>
