<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Campagnes</h1>
        <p class="text-muted mt-1 text-sm">Vos séquences de cold email, de l'envoi initial aux relances.</p>
      </div>
      <button class="btn-primary" @click="openCreateDrawer">
        <UIcon name="i-lucide-plus" class="h-4 w-4" />
        <span>Nouvelle campagne</span>
      </button>
    </div>

    <!-- Chargement -->
    <div v-if="campaignsStore.isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <template v-else-if="campaignsStore.campaignsCount > 0">
      <!-- Vue d'ensemble -->
      <div class="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div class="card p-3.5">
          <p class="app-label">Actives</p>
          <p class="mt-1 text-2xl font-bold text-[var(--app-green)] tabular-nums">{{ activeCampaignsCount }}</p>
        </div>
        <div class="card p-3.5">
          <p class="app-label">Prospects couverts</p>
          <p class="mt-1 text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ totalProspectsCovered }}</p>
        </div>
        <div class="card p-3.5">
          <p class="app-label">Emails envoyés</p>
          <p class="mt-1 text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ totalEmailsSent }}</p>
        </div>
        <div class="card p-3.5">
          <p class="app-label">Ouverture moyenne</p>
          <p class="mt-1 text-2xl font-bold text-[var(--app-violet)] tabular-nums">
            {{ averageOpenRate === null ? '—' : `${averageOpenRate}%` }}
          </p>
        </div>
      </div>

      <!-- Liste des campagnes — grille de cartes -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 2xl:grid-cols-3">
        <button
          v-for="campaign in campaignsStore.campaigns"
          :key="campaign.id"
          type="button"
          class="group card flex cursor-pointer flex-col gap-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)]"
          @click="router.push(`/dashboard/campaigns/${campaign.id}`)"
        >
          <!-- Header -->
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 items-center gap-2">
              <span class="h-2 w-2 shrink-0 rounded-full" :class="STATUS_DOT[campaign.status]"></span>
              <h3
                class="truncate text-sm font-semibold text-[var(--app-ink)] underline decoration-transparent underline-offset-4 transition-colors group-hover:decoration-[var(--app-accent)]"
              >
                {{ campaign.name }}
              </h3>
              <span
                v-if="campaign.ab_template_id_b"
                class="inline-flex shrink-0 items-center gap-1 rounded-full bg-[var(--app-violet-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--app-violet)]"
              >
                <UIcon name="i-lucide-flask-conical" class="h-2.5 w-2.5" /> A/B
              </span>
            </div>
            <span :class="['app-badge shrink-0', STATUS_STYLE[campaign.status] ?? '']">
              {{ CAMPAIGN_STATUS_LABELS[campaign.status] ?? campaign.status }}
            </span>
          </div>

          <p class="text-muted -mt-2 truncate text-xs">
            {{ campaign.description || `Créée le ${formatDate(campaign.created_at)}` }}
          </p>

          <!-- Metrics -->
          <div class="grid grid-cols-3 gap-3 rounded-lg bg-[var(--app-bg)] p-3">
            <div>
              <p class="font-label text-[9px] text-[var(--app-faint)] uppercase">Envoyés</p>
              <p class="mt-0.5 text-lg font-bold text-[var(--app-ink)] tabular-nums">
                {{ statsById[campaign.id]?.total_emails_sent ?? '—' }}
              </p>
            </div>
            <div>
              <p class="font-label text-[9px] text-[var(--app-faint)] uppercase">Ouverture</p>
              <p class="mt-0.5 text-lg font-bold text-[var(--app-violet)] tabular-nums">
                {{ statsById[campaign.id] ? `${statsById[campaign.id]?.open_rate ?? 0}%` : '—' }}
              </p>
              <div class="mt-1 h-1 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
                <div
                  class="h-full rounded-full bg-[var(--app-violet)] transition-all"
                  :style="{ width: `${Math.min(statsById[campaign.id]?.open_rate ?? 0, 100)}%` }"
                ></div>
              </div>
            </div>
            <div>
              <p class="font-label text-[9px] text-[var(--app-faint)] uppercase">Clic</p>
              <p class="mt-0.5 text-lg font-bold text-[var(--app-ink)] tabular-nums">
                {{ statsById[campaign.id] ? `${statsById[campaign.id]?.click_rate ?? 0}%` : '—' }}
              </p>
              <div class="mt-1 h-1 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
                <div
                  class="h-full rounded-full bg-[var(--app-ink)] transition-all"
                  :style="{ width: `${Math.min(statsById[campaign.id]?.click_rate ?? 0, 100)}%` }"
                ></div>
              </div>
            </div>
          </div>

          <!-- Footer meta -->
          <div class="flex items-center justify-between border-t border-[var(--app-line-soft)] pt-3">
            <div class="text-muted flex items-center gap-4 text-xs">
              <span class="flex items-center gap-1.5" title="Prospects dans la campagne">
                <UIcon name="i-lucide-users" class="h-3.5 w-3.5" />
                {{ campaign.prospects_count }}
              </span>
              <span class="flex items-center gap-1.5" title="Délai de relance">
                <UIcon name="i-lucide-reply" class="h-3.5 w-3.5" />
                J+{{ campaign.follow_up_delay_days }}
              </span>
            </div>
            <span
              class="app-label flex items-center gap-1 !text-[0.6rem] text-[var(--app-ink-soft)] transition-colors group-hover:!text-[var(--app-ink)]"
            >
              Ouvrir
              <UIcon name="i-lucide-arrow-right" class="h-3 w-3" />
            </span>
          </div>
        </button>
      </div>
    </template>

    <!-- État vide -->
    <div v-else class="card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucune campagne</h3>
      <p class="text-muted mx-auto mt-2 max-w-sm text-sm leading-relaxed">
        Créez une campagne pour envoyer vos premiers cold emails et leurs relances automatiques.
      </p>
      <div class="mt-6 flex justify-center">
        <button class="btn-primary" @click="openCreateDrawer">Créer ma première campagne</button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCampaignsStore } from '~/stores/campaigns'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { campaignService } from '~/services/campaignService'
import type { CampaignResponse, CampaignStats, CampaignStatus } from '~/services/campaignService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

// ─── Composables ──────────────────────────────────────────────────────────────

const campaignsStore = useCampaignsStore()
const router = useRouter()

// ─── Constants ────────────────────────────────────────────────────────────────

/** French labels for each campaign status value. */
const CAMPAIGN_STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: 'Brouillon',
  active: 'Active',
  completed: 'Terminée',
  paused: 'En pause',
  cancelled: 'Annulée',
}

/** app-badge variant per campaign status (semantic families of the app theme). */
const STATUS_STYLE: Record<CampaignStatus, string> = {
  draft: '',
  active: 'app-badge--success',
  completed: 'app-badge--info',
  paused: 'app-badge--progress',
  cancelled: 'app-badge--danger',
}

/** Dot classes per campaign status. */
const STATUS_DOT: Record<CampaignStatus, string> = {
  draft: 'bg-[var(--app-faint)]',
  active: 'bg-[var(--app-green)]',
  completed: 'bg-[var(--app-blue)]',
  paused: 'bg-[var(--app-accent)]',
  cancelled: 'bg-[var(--app-red)]',
}

// ─── State ────────────────────────────────────────────────────────────────────

/** Persistent drawer stack — campaign creation opens as a drawer, not a modal. */
const drawerStack = useDrawerStackStore()

/**
 * Open the campaign creation drawer.
 */
function openCreateDrawer(): void {
  drawerStack.push({ kind: 'create-campaign' })
}

/** Per-campaign stats (null while loading or when the fetch failed). */
const statsById: Ref<Record<number, CampaignStats | null>> = ref({})

// ─── Computed ─────────────────────────────────────────────────────────────────

/** Number of currently active campaigns. */
const activeCampaignsCount: ComputedRef<number> = computed((): number => {
  return campaignsStore.campaigns.filter((c: CampaignResponse): boolean => c.status === 'active').length
})

/** Prospects covered across every campaign. */
const totalProspectsCovered: ComputedRef<number> = computed((): number => {
  return campaignsStore.campaigns.reduce((sum: number, c: CampaignResponse): number => sum + c.prospects_count, 0)
})

/** Emails sent across every campaign (from the per-campaign stats). */
const totalEmailsSent: ComputedRef<number> = computed((): number => {
  return Object.values(statsById.value).reduce(
    (sum: number, stats: CampaignStats | null): number => sum + (stats?.total_emails_sent ?? 0),
    0,
  )
})

/** Average open rate across campaigns that sent at least one email. */
const averageOpenRate: ComputedRef<number | null> = computed((): number | null => {
  const relevant: CampaignStats[] = Object.values(statsById.value).filter(
    (stats: CampaignStats | null): stats is CampaignStats => stats !== null && stats.total_emails_sent > 0,
  )
  if (relevant.length === 0) return null
  const total: number = relevant.reduce((sum: number, stats: CampaignStats): number => sum + stats.open_rate, 0)
  return Math.round(total / relevant.length)
})

// ─── Data loading ─────────────────────────────────────────────────────────────

/**
 * Fetch the stats of every listed campaign in parallel (failures are ignored
 * so a single broken campaign never blanks the whole page).
 * @returns A promise that resolves once every fetch settled.
 */
async function loadStats(): Promise<void> {
  const campaigns: CampaignResponse[] = campaignsStore.campaigns
  const results: Array<{ id: number; stats: CampaignStats | null }> = await Promise.all(
    campaigns.map(
      async (campaign: CampaignResponse): Promise<{ id: number; stats: CampaignStats | null }> => ({
        id: campaign.id,
        stats: await campaignService.getStats(campaign.id).catch((): null => null),
      }),
    ),
  )
  const map: Record<number, CampaignStats | null> = {}
  for (const result of results) map[result.id] = result.stats
  statsById.value = map
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Format an ISO date string to a short French date.
 * @param dateStr - ISO date string from the API.
 * @returns Human-readable date (e.g. "1 juin 2026").
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })
}

// ─── Watchers ─────────────────────────────────────────────────────────────────

// Recharger les stats quand la liste change (création, fetch initial…).
watch(
  (): number => campaignsStore.campaignsCount,
  (): void => {
    void loadStats()
  },
)

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async (): Promise<void> => {
  await campaignsStore.fetchCampaigns()
  await loadStats()
})
</script>
