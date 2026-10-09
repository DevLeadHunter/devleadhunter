<template>
  <section
    v-if="videoSummary?.uses_video || (!videoSummary && loadErrorMessage)"
    class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5"
    aria-labelledby="campaign-videos-title"
  >
    <div class="mb-4 flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
      <div class="flex items-center gap-2">
        <UIcon name="i-lucide-clapperboard" class="h-4 w-4 text-[var(--app-ink)]" />
        <h3 id="campaign-videos-title" class="text-sm font-semibold text-[var(--app-ink)]">Vidéos</h3>
      </div>
      <p v-if="videoSummary" class="flex items-center gap-1.5 text-xs text-[var(--app-ink-soft)]">
        <UIcon
          :name="videoSummary.is_desktop_app_online ? 'i-lucide-monitor-check' : 'i-lucide-monitor-off'"
          class="h-3.5 w-3.5 shrink-0"
        />
        {{
          videoSummary.is_desktop_app_online
            ? 'Votre PC est allumé'
            : 'Votre PC est éteint : les vidéos se feront quand il sera allumé'
        }}
      </p>
    </div>

    <p v-if="loadErrorMessage" class="mb-3 flex flex-wrap items-center gap-x-2 text-xs text-[var(--app-red)]">
      {{ loadErrorMessage }}
      <button
        type="button"
        class="cursor-pointer font-medium underline underline-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="isLoadingSummary"
        @click="loadVideoSummary"
      >
        Réessayer
      </button>
    </p>

    <template v-if="videoSummary">
      <p v-if="videoStateLines.length === 0" class="text-sm text-[var(--app-ink-soft)]">
        Aucun prospect de la campagne n'a de site démo actif pour l'instant.
      </p>
      <ul
        v-else
        class="divide-y divide-[var(--app-line)] rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
      >
        <li v-for="line in videoStateLines" :key="line.key">
          <details class="group">
            <summary
              class="flex cursor-pointer list-none items-center gap-2.5 px-3 py-2.5 text-sm text-[var(--app-ink)] select-none [&::-webkit-details-marker]:hidden"
            >
              <UIcon
                :name="line.icon"
                :class="['h-4 w-4 shrink-0', line.iconClass, { 'animate-spin': line.key === 'building' }]"
              />
              <span class="min-w-0 flex-1">{{ line.label }}</span>
              <UIcon
                name="i-lucide-chevron-down"
                class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)] transition-transform group-open:rotate-180"
              />
            </summary>
            <ul class="space-y-1 px-3 pb-3 pl-9.5">
              <li v-for="site in line.sites" :key="site.demo_site_id">
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

      <div class="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          class="app-btn-primary h-8 px-3 text-xs"
          :disabled="missingVideoCount === 0 || isRequestingVideos"
          @click="requestVideos('missing')"
        >
          <UIcon name="i-lucide-clapperboard" class="h-3.5 w-3.5" />
          {{ requestingVideosScope === 'missing' ? 'Envoi à votre PC…' : 'Générer les vidéos manquantes' }}
        </button>
        <button
          type="button"
          class="app-btn-secondary h-8 px-3 text-xs"
          :disabled="redoableVideoCount === 0 || isRequestingVideos"
          @click="redoConfirmModal?.open()"
        >
          <UIcon name="i-lucide-refresh-cw" class="h-3.5 w-3.5" />
          {{ requestingVideosScope === 'all' ? 'Envoi à votre PC…' : 'Refaire toutes les vidéos' }}
        </button>
      </div>

      <details
        v-if="lastRequestSkippedSites.length > 0"
        class="group mt-3 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
      >
        <summary
          class="text-muted flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-xs font-medium select-none hover:text-[var(--app-ink)] [&::-webkit-details-marker]:hidden"
        >
          <span class="flex items-center gap-2">
            <UIcon name="i-lucide-circle-slash" class="h-3.5 w-3.5 shrink-0" />
            {{ lastRequestSkippedSitesLabel }}
          </span>
          <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 shrink-0 transition-transform group-open:rotate-180" />
        </summary>
        <ul class="space-y-1.5 border-t border-[var(--app-line)] px-3 py-3">
          <li v-for="site in lastRequestSkippedSites" :key="site.demo_site_id" class="text-xs leading-relaxed">
            <NuxtLink
              :to="`/dashboard/demo-sites/${site.demo_site_id}`"
              class="font-medium text-[var(--app-ink)] underline-offset-2 hover:underline"
            >
              {{ site.business_name }}
            </NuxtLink>
            <span class="text-[var(--app-ink-soft)]"> : {{ site.reason }}</span>
          </li>
        </ul>
      </details>
    </template>

    <UiConfirmModal
      ref="redoConfirmModal"
      title="Refaire toutes les vidéos"
      message="Votre PC refera toutes les vidéos de la campagne, même celles déjà faites avec votre clip actuel. Chaque vidéo en ligne le reste jusqu'à ce que la nouvelle la remplace."
      confirm-text="Tout refaire"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="requestVideos('all')"
    />
  </section>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type {
  CampaignVideoRequestsResponse,
  CampaignVideoSkippedSite,
  CampaignVideosResponse,
} from '~/types/CampaignVideos'
import type {
  CampaignVideoStateLine,
  CampaignVideoStateWording,
  CampaignVideosCardProps,
  CampaignVideosRequestScope,
} from '~/types/CampaignVideosCard'
import type { UseToastReturn } from '~/types/Composables'
import type { UiConfirmModalHandle } from '~/types/UiConfirmModal'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useToast } from '~/composables/useToast'
import { CampaignService } from '~/services/campaignService'
import { CampaignResultsFormat } from '~/utils/campaignResultsFormat'

/** Where the videos of the campaign's demo sites stand, with the buttons that ask the owner's PC for them. */
const props: CampaignVideosCardProps = defineProps({
  campaignId: {
    type: Number,
    required: true,
  },
})

const toast: UseToastReturn = useToast()

const SUMMARY_REFRESH_INTERVAL_MS: number = 20_000

const VIDEO_STATE_WORDINGS: CampaignVideoStateWording[] = [
  {
    key: 'ready',
    icon: 'i-lucide-circle-check',
    iconClass: 'text-[var(--app-green)]',
    singularLabel: 'vidéo prête',
    pluralLabel: 'vidéos prêtes',
  },
  {
    key: 'ready_with_older_clip',
    icon: 'i-lucide-history',
    iconClass: 'text-[var(--app-accent-ink)]',
    singularLabel: 'vidéo faite avec un ancien clip',
    pluralLabel: 'vidéos faites avec un ancien clip',
  },
  {
    key: 'building',
    icon: 'i-lucide-loader-circle',
    iconClass: 'text-[var(--app-ink-soft)]',
    singularLabel: 'vidéo en cours sur votre PC',
    pluralLabel: 'vidéos en cours sur votre PC',
  },
  {
    key: 'waiting_for_desktop',
    icon: 'i-lucide-monitor',
    iconClass: 'text-[var(--app-ink-soft)]',
    singularLabel: 'vidéo en attente de votre PC',
    pluralLabel: 'vidéos en attente de votre PC',
  },
  {
    key: 'waiting_for_storyblok_space',
    icon: 'i-lucide-hourglass',
    iconClass: 'text-[var(--app-ink-soft)]',
    singularLabel: "vidéo en attente de l'espace Storyblok de son site",
    pluralLabel: "vidéos en attente de l'espace Storyblok de leur site",
  },
  {
    key: 'failed',
    icon: 'i-lucide-circle-x',
    iconClass: 'text-[var(--app-red)]',
    singularLabel: 'vidéo en échec',
    pluralLabel: 'vidéos en échec',
  },
  {
    key: 'not_requested',
    icon: 'i-lucide-video-off',
    iconClass: 'text-[var(--app-ink-soft)]',
    singularLabel: 'site sans vidéo',
    pluralLabel: 'sites sans vidéo',
  },
]

const videoSummary: Ref<CampaignVideosResponse | null> = ref(null)
const loadErrorMessage: Ref<string> = ref('')
const isLoadingSummary: Ref<boolean> = ref(false)
const requestingVideosScope: Ref<CampaignVideosRequestScope | null> = ref(null)
const lastRequestSkippedSites: Ref<CampaignVideoSkippedSite[]> = ref([])
const redoConfirmModal: Ref<UiConfirmModalHandle | null> = ref(null)

let summaryRefreshTimer: ReturnType<typeof setTimeout> | null = null
let latestSummaryLoadNumber: number = 0
let isCardUnmounted: boolean = false

const videoStateLines: ComputedRef<CampaignVideoStateLine[]> = computed((): CampaignVideoStateLine[] => {
  const summary: CampaignVideosResponse | null = videoSummary.value
  if (!summary) {
    return []
  }
  return VIDEO_STATE_WORDINGS.filter(
    (wording: CampaignVideoStateWording): boolean => summary[wording.key].length > 0,
  ).map(
    (wording: CampaignVideoStateWording): CampaignVideoStateLine => ({
      key: wording.key,
      icon: wording.icon,
      iconClass: wording.iconClass,
      label: CampaignResultsFormat.count(summary[wording.key].length, wording.singularLabel, wording.pluralLabel),
      sites: summary[wording.key],
    }),
  )
})

const missingVideoCount: ComputedRef<number> = computed((): number => {
  const summary: CampaignVideosResponse | null = videoSummary.value
  if (!summary) {
    return 0
  }
  return summary.ready_with_older_clip.length + summary.failed.length + summary.not_requested.length
})

const redoableVideoCount: ComputedRef<number> = computed(
  (): number => missingVideoCount.value + (videoSummary.value?.ready.length ?? 0),
)

const hasVideosUnderWay: ComputedRef<boolean> = computed((): boolean => {
  const summary: CampaignVideosResponse | null = videoSummary.value
  if (!summary) {
    return false
  }
  return summary.building.length + summary.waiting_for_desktop.length + summary.waiting_for_storyblok_space.length > 0
})

const isRequestingVideos: ComputedRef<boolean> = computed((): boolean => requestingVideosScope.value !== null)

const lastRequestSkippedSitesLabel: ComputedRef<string> = computed((): string =>
  CampaignResultsFormat.count(lastRequestSkippedSites.value.length, 'site laissé de côté', 'sites laissés de côté'),
)

/**
 * Read where the campaign's videos stand.
 * @returns A promise resolved once the state is shown, or the failure is.
 */
async function loadVideoSummary(): Promise<void> {
  latestSummaryLoadNumber += 1
  const loadNumber: number = latestSummaryLoadNumber
  isLoadingSummary.value = true
  try {
    const summary: CampaignVideosResponse = await CampaignService.getVideos(props.campaignId)
    if (loadNumber === latestSummaryLoadNumber) {
      videoSummary.value = summary
      loadErrorMessage.value = ''
    }
  } catch {
    if (loadNumber === latestSummaryLoadNumber) {
      loadErrorMessage.value = "L'état des vidéos n'a pas pu être lu."
    }
  } finally {
    if (loadNumber === latestSummaryLoadNumber) {
      isLoadingSummary.value = false
      scheduleSummaryRefresh()
    }
  }
}

/** Plan the next read in 20 s while a video waits or is being built, so the counts follow the PC. */
function scheduleSummaryRefresh(): void {
  stopSummaryRefresh()
  if (isCardUnmounted || !hasVideosUnderWay.value) {
    return
  }
  summaryRefreshTimer = setTimeout((): void => {
    summaryRefreshTimer = null
    if (document.visibilityState === 'visible') {
      loadVideoSummary()
      return
    }
    scheduleSummaryRefresh()
  }, SUMMARY_REFRESH_INTERVAL_MS)
}

/** Stop the planned read. */
function stopSummaryRefresh(): void {
  if (summaryRefreshTimer !== null) {
    clearTimeout(summaryRefreshTimer)
    summaryRefreshTimer = null
  }
}

/**
 * Ask the owner's PC for the campaign's missing videos, or for all of them.
 * @param scope - `missing` for the videos the sites lack or made with an older clip, `all` to redo every one.
 * @returns A promise resolved once the videos are asked and the counts re-read, or the request was refused.
 */
async function requestVideos(scope: CampaignVideosRequestScope): Promise<void> {
  if (isRequestingVideos.value) {
    return
  }
  requestingVideosScope.value = scope
  try {
    const outcome: CampaignVideoRequestsResponse = await CampaignService.requestVideos(
      props.campaignId,
      scope === 'all',
    )
    lastRequestSkippedSites.value = outcome.skipped
    if (outcome.requested_count > 0) {
      toast.success(
        `${CampaignResultsFormat.count(outcome.requested_count, 'vidéo demandée', 'vidéos demandées')} à votre PC.`,
      )
    } else {
      toast.info('Aucune vidéo à demander.')
    }
    await loadVideoSummary()
  } catch (error: unknown) {
    toast.error(
      error instanceof Error && error.message ? error.message : "Les vidéos n'ont pas pu être demandées à votre PC.",
    )
  } finally {
    requestingVideosScope.value = null
  }
}

watch(
  (): number => props.campaignId,
  (): void => {
    loadVideoSummary()
  },
)

onMounted((): void => {
  loadVideoSummary()
})

onBeforeUnmount((): void => {
  isCardUnmounted = true
  stopSummaryRefresh()
})
</script>
