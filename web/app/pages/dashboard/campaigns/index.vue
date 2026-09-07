<template>
  <div class="space-y-5">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Campagnes</h1>
        <p class="text-muted mt-1 text-sm">Vos séquences de cold email, de l'envoi initial aux relances.</p>
      </div>
      <div class="flex items-center gap-3">
        <div
          class="inline-flex gap-0.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] p-0.5"
          role="tablist"
          aria-label="Vue"
        >
          <button
            v-for="option in VIEW_OPTIONS"
            :key="option.key"
            type="button"
            role="tab"
            :aria-selected="view === option.key"
            :class="[
              'inline-flex cursor-pointer items-center gap-1.5 rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors',
              view === option.key
                ? 'bg-[var(--app-ink)] text-[var(--app-bg)]'
                : 'text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
            ]"
            @click="view = option.key"
          >
            <UIcon :name="option.icon" class="h-3.5 w-3.5" />
            {{ option.label }}
          </button>
        </div>
        <button class="btn-primary" @click="openCreateDrawer">
          <UIcon name="i-lucide-plus" class="h-4 w-4" />
          <span>Nouvelle campagne</span>
        </button>
      </div>
    </div>

    <UiCampaignForecast v-if="view === 'forecast'" />

    <template v-else>
      <div v-if="campaignsStore.isLoading && campaignsStore.campaignsCount === 0" class="card">
        <div class="animate-pulse space-y-3">
          <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
          <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>

      <template v-else-if="campaignsStore.campaignsCount > 0">
        <div class="grid grid-cols-2 gap-3 @4xl:grid-cols-4">
          <div class="card p-3.5">
            <p class="app-label">Actives</p>
            <p class="mt-1 text-2xl font-bold text-[var(--app-green)] tabular-nums">{{ activeCampaignsCount }}</p>
          </div>
          <div class="card p-3.5">
            <p class="app-label">Prochains envois · 7 j</p>
            <p class="mt-1 text-2xl font-bold text-[var(--app-ink)] tabular-nums">
              {{ campaignsStore.upcomingSends7d }}
            </p>
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

        <!-- Filtres : recherche à gauche, tri + période à droite. -->
        <div class="card p-3">
          <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
            <div class="relative w-full @2xl:max-w-xs">
              <UIcon
                name="i-lucide-search"
                class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
              />
              <input
                v-model="searchQuery"
                type="search"
                placeholder="Rechercher une campagne…"
                aria-label="Rechercher une campagne"
                class="app-input pl-9"
              />
            </div>

            <div class="flex items-center gap-2">
              <div ref="sortMenuEl" class="relative">
                <button
                  type="button"
                  class="app-btn-secondary h-9 px-4 text-xs whitespace-nowrap"
                  :aria-expanded="isSortMenuOpen"
                  aria-haspopup="menu"
                  @click="isSortMenuOpen = !isSortMenuOpen"
                >
                  <UIcon name="i-lucide-arrow-up-down" class="h-3.5 w-3.5" />
                  <span>{{ sortLabel }}</span>
                  <UIcon
                    name="i-lucide-chevron-down"
                    :class="['h-3 w-3 opacity-60 transition-transform', isSortMenuOpen && 'rotate-180']"
                  />
                </button>
                <div
                  v-if="isSortMenuOpen"
                  class="absolute right-0 z-50 mt-1.5 w-52 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1.5 shadow-[var(--app-shadow-soft)]"
                  role="menu"
                >
                  <button
                    v-for="option in SORT_OPTIONS"
                    :key="option.key"
                    type="button"
                    role="menuitemradio"
                    :aria-checked="sortKey === option.key"
                    class="flex w-full cursor-pointer items-center justify-between rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                    @click="selectSort(option.key)"
                  >
                    {{ option.label }}
                    <UIcon
                      v-if="sortKey === option.key"
                      name="i-lucide-check"
                      class="h-3.5 w-3.5 text-[var(--app-accent-ink)]"
                    />
                  </button>
                </div>
              </div>

              <UiPeriodFilter v-model="period" />
            </div>
          </div>
        </div>

        <!-- Onglets de statut, hors carte : la ligne porte le trait, l'onglet actif le souligne. -->
        <div class="border-b border-[var(--app-line)]">
          <UiFilterTabs
            :model-value="statusTab"
            :tabs="statusTabs"
            @update:model-value="statusTab = $event as StatusTabKey"
          />
        </div>

        <div class="flex min-h-[26px] flex-wrap items-center justify-between gap-2">
          <div class="flex flex-wrap items-center gap-2">
            <span class="app-label">{{ resultCountLabel }}</span>
            <span
              v-if="searchQuery.trim()"
              class="inline-flex items-center gap-1.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] py-0.5 pr-1 pl-2.5 text-xs text-[var(--app-ink)]"
            >
              « {{ searchQuery.trim() }} »
              <button
                type="button"
                class="flex rounded-full p-0.5 text-[var(--app-faint)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                aria-label="Retirer la recherche"
                @click="searchQuery = ''"
              >
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </span>
            <span
              v-if="period.preset !== 'all'"
              class="inline-flex items-center gap-1.5 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)] py-0.5 pr-1 pl-2.5 text-xs text-[var(--app-ink)]"
            >
              {{ periodChipLabel }}
              <button
                type="button"
                class="flex rounded-full p-0.5 text-[var(--app-faint)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                aria-label="Retirer la période"
                @click="period = { preset: 'all', start: null, end: null }"
              >
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </span>
          </div>
          <button
            v-if="hasActiveFilters"
            type="button"
            class="cursor-pointer text-xs text-[var(--app-ink-soft)] underline decoration-[var(--app-line)] underline-offset-2 transition-colors hover:text-[var(--app-ink)] hover:decoration-[var(--app-ink)]"
            @click="resetFilters"
          >
            Réinitialiser les filtres
          </button>
        </div>

        <div v-if="visibleCampaigns.length > 0" class="grid grid-cols-1 gap-4 @sm:grid-cols-2 @6xl:grid-cols-3">
          <div
            v-for="campaign in visibleCampaigns"
            :key="campaign.id"
            class="group card relative flex cursor-pointer flex-col gap-4 text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)]"
            role="link"
            tabindex="0"
            :aria-label="`Ouvrir la campagne ${campaign.name}`"
            @click="openCampaign(campaign.id)"
            @keydown.enter.prevent="openCampaign(campaign.id)"
            @keydown.space.prevent="openCampaign(campaign.id)"
          >
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
                <span
                  v-if="campaign.channel === 'sms'"
                  class="inline-flex shrink-0 items-center gap-1 rounded-full bg-[var(--app-accent-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
                >
                  <UIcon name="i-lucide-message-square-text" class="h-2.5 w-2.5" /> SMS
                </span>
              </div>
              <div class="flex shrink-0 items-center gap-1.5">
                <span :class="['app-badge shrink-0', STATUS_STYLE[campaign.status] ?? '']">
                  {{ CAMPAIGN_STATUS_LABELS[campaign.status] ?? campaign.status }}
                </span>
                <div class="relative">
                  <button
                    type="button"
                    class="flex rounded-md p-1 text-[var(--app-faint)] opacity-0 transition-all group-hover:opacity-100 hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)] focus-visible:opacity-100"
                    :aria-expanded="openMenuId === campaign.id"
                    aria-haspopup="menu"
                    aria-label="Actions de la campagne"
                    @click.stop="toggleMenu(campaign.id)"
                    @keydown.enter.stop
                    @keydown.space.stop
                  >
                    <UIcon name="i-lucide-more-horizontal" class="h-4 w-4" />
                  </button>
                  <template v-if="openMenuId === campaign.id">
                    <div class="fixed inset-0 z-40" @click.stop="openMenuId = null"></div>
                    <div
                      class="absolute right-0 z-50 mt-1 w-48 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-1.5 shadow-[var(--app-shadow-soft)]"
                      role="menu"
                    >
                      <button
                        v-if="campaign.status === 'active'"
                        type="button"
                        class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                        @click.stop="pauseCampaign(campaign)"
                      >
                        <UIcon name="i-lucide-pause" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                        Mettre en pause
                      </button>
                      <button
                        v-else-if="campaign.status === 'paused'"
                        type="button"
                        class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                        @click.stop="resumeCampaign(campaign)"
                      >
                        <UIcon name="i-lucide-play" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                        Reprendre
                      </button>
                      <button
                        type="button"
                        class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-ink)] transition-colors hover:bg-[var(--app-surface-2)]"
                        @click.stop="editCampaign(campaign)"
                      >
                        <UIcon name="i-lucide-pencil" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
                        Modifier
                      </button>
                      <div class="my-1 h-px bg-[var(--app-line)]"></div>
                      <button
                        type="button"
                        class="flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-left text-xs font-medium text-[var(--app-red)] transition-colors hover:bg-[var(--app-red-soft)]"
                        @click.stop="askDelete(campaign)"
                      >
                        <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                        Supprimer
                      </button>
                    </div>
                  </template>
                </div>
              </div>
            </div>

            <p class="text-muted -mt-2 truncate text-xs">
              {{ campaign.description || `Créée le ${formatLongMonthDate(campaign.created_at)}` }}
            </p>

            <span
              v-if="campaign.status === 'active' && campaign.next_send_at"
              class="-mt-1 inline-flex items-center gap-1.5 self-start rounded-full bg-[var(--app-accent-soft)] px-2.5 py-1 text-xs text-[var(--app-accent-ink)]"
            >
              <UIcon name="i-lucide-clock" class="h-3 w-3" />
              Prochain envoi · {{ formatNextSend(campaign.next_send_at) }}
            </span>

            <div v-if="campaign.channel !== 'sms'" class="grid grid-cols-3 gap-3 rounded-lg bg-[var(--app-bg)] p-3">
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

            <div v-else class="rounded-lg bg-[var(--app-bg)] p-3">
              <div class="flex items-center gap-2">
                <UIcon name="i-lucide-message-square-text" class="h-3.5 w-3.5 text-[var(--app-accent-ink)]" />
                <p class="font-label text-[9px] text-[var(--app-faint)] uppercase">Campagne SMS</p>
              </div>
              <p class="mt-0.5 text-lg font-bold text-[var(--app-ink)] tabular-nums">
                {{ campaign.prospects_count }}
                <span class="text-xs font-medium text-[var(--app-ink-soft)]">
                  prospect{{ campaign.prospects_count !== 1 ? 's' : '' }}
                </span>
              </p>
            </div>

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
          </div>
        </div>

        <div v-else class="card px-6 py-12 text-center">
          <UIcon name="i-lucide-search-x" class="mx-auto h-8 w-8 text-[var(--app-faint)]" />
          <h3 class="font-display mt-4 text-lg font-semibold text-[var(--app-ink)]">Aucune campagne ne correspond</h3>
          <p class="text-muted mx-auto mt-2 max-w-sm text-sm leading-relaxed">{{ filteredEmptyMessage }}</p>
          <div class="mt-5 flex justify-center">
            <button class="app-btn-secondary h-9 px-4 text-xs" @click="resetFilters">Réinitialiser les filtres</button>
          </div>
        </div>
      </template>

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

      <UiConfirmModal
        ref="deleteModal"
        title="Supprimer la campagne"
        :message="deleteMessage"
        confirm-text="Supprimer"
        cancel-text="Annuler"
        confirm-button-variant="danger"
        @confirm="confirmDelete"
      />
    </template>
  </div>
</template>

<script lang="ts" setup>
import { formatLongMonthDate, parseApiDate } from '~/utils/date'
import { computed, onMounted, ref, watch } from 'vue'
import type { ComputedRef, Ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { LocationQuery } from 'vue-router'
import { onClickOutside } from '@vueuse/core'
import { useCampaignsStore } from '~/stores/campaigns'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { useToast } from '~/composables/useToast'
import { CampaignService } from '~/services/campaignService'
import type {
  CampaignDetailResponse,
  CampaignResponse,
  CampaignStats,
  CampaignStatus,
} from '~/services/campaignService'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import type { PeriodPreset, PeriodValue } from '~/types/UiPeriodFilter'
import type { UseToastReturn } from '~/types/Composables'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

/** How the campaign list is ordered. */
type CampaignSortKey = 'recent' | 'next' | 'open' | 'prospects'

/** One selectable sort option. */
type SortOption = { key: CampaignSortKey; label: string }

/** Which status group the tabs slice the list into. */
type StatusTabKey = 'ongoing' | 'draft' | 'done' | 'all'

/** Which view of the campaigns page is shown: the list, or the week-ahead forecast. */
type CampaignView = 'list' | 'forecast'

/** One selectable view of the campaigns page. */
type ViewOption = { key: CampaignView; label: string; icon: string }

/** Minimal shape exposed by `UiConfirmModal` via `defineExpose`. */
type ConfirmModalHandle = { open: () => void; close: () => void }

const campaignsStore: ReturnType<typeof useCampaignsStore> = useCampaignsStore()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
const router: ReturnType<typeof useRouter> = useRouter()
const route: ReturnType<typeof useRoute> = useRoute()
const toast: UseToastReturn = useToast()

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

/** Which status tab a campaign status belongs to. */
const STATUS_BUCKET: Record<CampaignStatus, Exclude<StatusTabKey, 'all'>> = {
  active: 'ongoing',
  paused: 'ongoing',
  draft: 'draft',
  completed: 'done',
  cancelled: 'done',
}

/** Page views, in display order. */
const VIEW_OPTIONS: ViewOption[] = [
  { key: 'list', label: 'Liste', icon: 'i-lucide-layout-grid' },
  { key: 'forecast', label: 'Prévisionnel', icon: 'i-lucide-calendar-days' },
]

/** Sort options, in display order. */
const SORT_OPTIONS: SortOption[] = [
  { key: 'recent', label: 'Plus récentes' },
  { key: 'next', label: 'Prochain envoi' },
  { key: 'open', label: "Taux d'ouverture" },
  { key: 'prospects', label: 'Nb de prospects' },
]

/** Human label of each status tab. */
const TAB_LABELS: Record<StatusTabKey, string> = {
  ongoing: 'En cours',
  draft: 'Brouillons',
  done: 'Terminées',
  all: 'Toutes',
}

// Vue active de la page (liste ou prévisionnel), et état réactif des filtres de la liste.
const view: Ref<CampaignView> = ref('list')
const searchQuery: Ref<string> = ref('')
const statusTab: Ref<StatusTabKey> = ref('ongoing')
const sortKey: Ref<CampaignSortKey> = ref('recent')
const period: Ref<PeriodValue> = ref({ preset: 'all', start: null, end: null })
const isSortMenuOpen: Ref<boolean> = ref(false)
const sortMenuEl: Ref<HTMLElement | null> = ref(null)
const openMenuId: Ref<number | null> = ref(null)

/** Per-campaign stats (null while loading or when the fetch failed). */
const statsById: Ref<Record<number, CampaignStats | null>> = ref({})

/** The confirm dialog instance and the campaign awaiting deletion. */
const deleteModal: Ref<ConfirmModalHandle | null> = ref(null)
const campaignPendingDelete: Ref<CampaignResponse | null> = ref(null)

onClickOutside(sortMenuEl, (): void => {
  isSortMenuOpen.value = false
})

/** Label of the active sort option. */
const sortLabel: ComputedRef<string> = computed(
  (): string =>
    SORT_OPTIONS.find((option: SortOption): boolean => option.key === sortKey.value)?.label ?? 'Plus récentes',
)

/** Campaigns matching the search + period (before the status tab slices them). */
const searchedCampaigns: ComputedRef<CampaignResponse[]> = computed((): CampaignResponse[] => {
  const query: string = searchQuery.value.trim().toLowerCase()
  return campaignsStore.campaigns.filter((campaign: CampaignResponse): boolean => {
    const matchesQuery: boolean =
      !query ||
      campaign.name.toLowerCase().includes(query) ||
      (campaign.description?.toLowerCase().includes(query) ?? false)
    return matchesQuery && matchesPeriod(campaign)
  })
})

/** Count of campaigns in each status tab, reflecting the search + period. */
const tabCounts: ComputedRef<Record<StatusTabKey, number>> = computed((): Record<StatusTabKey, number> => {
  const counts: Record<StatusTabKey, number> = { ongoing: 0, draft: 0, done: 0, all: searchedCampaigns.value.length }
  for (const campaign of searchedCampaigns.value) counts[STATUS_BUCKET[campaign.status]]++
  return counts
})

/** Tab descriptors passed to `UiFilterTabs`. */
const statusTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] =>
  (Object.keys(TAB_LABELS) as StatusTabKey[]).map(
    (key: StatusTabKey): UiFilterTab => ({ key, label: TAB_LABELS[key], count: tabCounts.value[key] }),
  ),
)

/** Campaigns shown in the grid: search + period + status tab, sorted. */
const visibleCampaigns: ComputedRef<CampaignResponse[]> = computed((): CampaignResponse[] => {
  const inTab: CampaignResponse[] = searchedCampaigns.value.filter(
    (campaign: CampaignResponse): boolean =>
      statusTab.value === 'all' || STATUS_BUCKET[campaign.status] === statusTab.value,
  )
  return sortCampaigns(inTab)
})

/** Whether any filter deviates from the default view. */
const hasActiveFilters: ComputedRef<boolean> = computed(
  (): boolean =>
    searchQuery.value.trim() !== '' ||
    period.value.preset !== 'all' ||
    sortKey.value !== 'recent' ||
    statusTab.value !== 'ongoing',
)

/** `N campagnes · <onglet>` shown above the grid. */
const resultCountLabel: ComputedRef<string> = computed((): string => {
  const count: number = visibleCampaigns.value.length
  return `${count} campagne${count > 1 ? 's' : ''} · ${TAB_LABELS[statusTab.value]}`
})

/** Chip label describing the active period. */
const periodChipLabel: ComputedRef<string> = computed((): string => {
  if (period.value.preset === 'month') return 'Ce mois-ci'
  if (period.value.preset === '30d') return '30 derniers jours'
  if (period.value.preset === 'custom' && period.value.start && period.value.end) {
    return `${formatLongMonthDate(period.value.start)} → ${formatLongMonthDate(period.value.end)}`
  }
  return 'Période'
})

/** Message of the filtered-empty panel, tuned to the active search. */
const filteredEmptyMessage: ComputedRef<string> = computed((): string =>
  searchQuery.value.trim()
    ? `Rien pour « ${searchQuery.value.trim()} » dans « ${TAB_LABELS[statusTab.value]} ». Élargissez la recherche ou changez d'onglet.`
    : `Aucune campagne dans « ${TAB_LABELS[statusTab.value]} » pour ces filtres.`,
)

/** Confirmation message of the delete dialog. */
const deleteMessage: ComputedRef<string> = computed((): string =>
  campaignPendingDelete.value
    ? `Supprimer « ${campaignPendingDelete.value.name} » et toute sa file d'envoi ? Cette action est irréversible.`
    : '',
)

/** Number of currently active campaigns. */
const activeCampaignsCount: ComputedRef<number> = computed(
  (): number => campaignsStore.campaigns.filter((c: CampaignResponse): boolean => c.status === 'active').length,
)

/** Emails sent across every campaign (from the per-campaign stats). */
const totalEmailsSent: ComputedRef<number> = computed((): number =>
  Object.values(statsById.value).reduce(
    (sum: number, stats: CampaignStats | null): number => sum + (stats?.total_emails_sent ?? 0),
    0,
  ),
)

/** Average open rate across campaigns that sent at least one email. */
const averageOpenRate: ComputedRef<number | null> = computed((): number | null => {
  const relevant: CampaignStats[] = Object.values(statsById.value).filter(
    (stats: CampaignStats | null): stats is CampaignStats => stats !== null && stats.total_emails_sent > 0,
  )
  if (relevant.length === 0) return null
  const total: number = relevant.reduce((sum: number, stats: CampaignStats): number => sum + stats.open_rate, 0)
  return Math.round(total / relevant.length)
})

/**
 * Return the Monday 00:00 of the week containing `date` (local time).
 * @param date - Any date in the target week.
 * @returns Midnight on that week's Monday.
 */
function startOfWeek(date: Date): Date {
  const mondayOffset: number = (date.getDay() + 6) % 7
  return new Date(date.getFullYear(), date.getMonth(), date.getDate() - mondayOffset, 0, 0, 0, 0)
}

/**
 * Whether a campaign's send window (not its creation date) overlaps the active period filter.
 * @param campaign - The campaign to test.
 * @returns True when the campaign passes the period filter.
 */
function matchesPeriod(campaign: CampaignResponse): boolean {
  if (period.value.preset === 'all') return true
  const now: Date = new Date()
  let start: Date
  let end: Date
  if (period.value.preset === 'week') {
    start = startOfWeek(now)
    end = new Date(start)
    end.setDate(end.getDate() + 6)
    end.setHours(23, 59, 59, 999)
  } else if (period.value.preset === 'month') {
    start = new Date(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0)
    end = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59, 999)
  } else if (period.value.preset === '30d') {
    start = new Date(now)
    start.setDate(start.getDate() - 30)
    end = now
  } else if (period.value.preset === 'custom' && period.value.start && period.value.end) {
    const startParts: string[] = period.value.start.split('-')
    const endParts: string[] = period.value.end.split('-')
    start = new Date(Number(startParts[0]), Number(startParts[1]) - 1, Number(startParts[2]), 0, 0, 0, 0)
    end = new Date(Number(endParts[0]), Number(endParts[1]) - 1, Number(endParts[2]), 23, 59, 59, 999)
  } else {
    return true
  }
  // Fenêtre d'envoi réelle ; avant lancement (file vide) on retombe sur la date de création.
  const windowStart: Date = campaign.first_send_at
    ? parseApiDate(campaign.first_send_at)
    : parseApiDate(campaign.created_at)
  const windowEnd: Date = campaign.last_send_at ? parseApiDate(campaign.last_send_at) : windowStart
  return windowStart <= end && windowEnd >= start
}

/**
 * Sort a campaign list by the active sort key (returns a new array).
 * @param list - The campaigns to sort.
 * @returns The sorted campaigns.
 */
function sortCampaigns(list: CampaignResponse[]): CampaignResponse[] {
  const sorted: CampaignResponse[] = [...list]
  if (sortKey.value === 'recent') {
    sorted.sort(
      (a: CampaignResponse, b: CampaignResponse): number =>
        parseApiDate(b.created_at).getTime() - parseApiDate(a.created_at).getTime(),
    )
  } else if (sortKey.value === 'prospects') {
    sorted.sort((a: CampaignResponse, b: CampaignResponse): number => b.prospects_count - a.prospects_count)
  } else if (sortKey.value === 'open') {
    sorted.sort(
      (a: CampaignResponse, b: CampaignResponse): number =>
        (statsById.value[b.id]?.open_rate ?? -1) - (statsById.value[a.id]?.open_rate ?? -1),
    )
  } else if (sortKey.value === 'next') {
    sorted.sort((a: CampaignResponse, b: CampaignResponse): number => nextSendTime(a) - nextSendTime(b))
  }
  return sorted
}

/**
 * Sortable next-send timestamp, `Infinity` when none is scheduled (pending campaigns sort last).
 * @param campaign - The campaign to read.
 * @returns The next-send epoch, or `Infinity`.
 */
function nextSendTime(campaign: CampaignResponse): number {
  return campaign.next_send_at ? parseApiDate(campaign.next_send_at).getTime() : Number.POSITIVE_INFINITY
}

/**
 * Format a next-send datetime as `Aujourd'hui 09:12`, `Demain 09:12`, or `1 juin 09:12`.
 * @param iso - The scheduled datetime (naive UTC from the API).
 * @returns The friendly label.
 */
function formatNextSend(iso: string): string {
  const date: Date = parseApiDate(iso)
  const now: Date = new Date()
  const time: string = date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  const tomorrow: Date = new Date(now)
  tomorrow.setDate(tomorrow.getDate() + 1)
  const sameDay: (a: Date, b: Date) => boolean = (a: Date, b: Date): boolean =>
    a.getDate() === b.getDate() && a.getMonth() === b.getMonth() && a.getFullYear() === b.getFullYear()
  if (sameDay(date, now)) return `Aujourd'hui ${time}`
  if (sameDay(date, tomorrow)) return `Demain ${time}`
  return `${date.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })} ${time}`
}

/**
 * Open the campaign creation drawer.
 */
function openCreateDrawer(): void {
  drawerStack.push({ kind: 'campaign-form', mode: 'create', campaign: null })
}

/**
 * Navigate to a campaign's detail page.
 * @param id - Campaign identifier.
 */
function openCampaign(id: number): void {
  void router.push(`/dashboard/campaigns/${id}`)
}

/**
 * Select a sort option and close the sort menu.
 * @param key - The chosen sort key.
 */
function selectSort(key: CampaignSortKey): void {
  sortKey.value = key
  isSortMenuOpen.value = false
}

/**
 * Toggle a campaign card's action menu (closing any other open one).
 * @param id - Campaign identifier.
 */
function toggleMenu(id: number): void {
  openMenuId.value = openMenuId.value === id ? null : id
}

/**
 * Reset every filter back to the default view.
 */
function resetFilters(): void {
  searchQuery.value = ''
  statusTab.value = 'ongoing'
  sortKey.value = 'recent'
  period.value = { preset: 'all', start: null, end: null }
}

/**
 * Refetch the campaign list and reload its stats.
 * @returns A promise resolving once both settled.
 */
async function reload(): Promise<void> {
  await campaignsStore.fetchCampaigns()
  await loadStats()
}

/**
 * Pause a running campaign, then refresh the list.
 * @param campaign - The campaign to pause.
 * @returns A promise resolving once the list refreshed.
 */
async function pauseCampaign(campaign: CampaignResponse): Promise<void> {
  openMenuId.value = null
  try {
    await CampaignService.pause(campaign.id)
    toast.success(`« ${campaign.name} » mise en pause`)
    await reload()
  } catch {
    toast.error('Échec de la mise en pause')
  }
}

/**
 * Resume a paused campaign, then refresh the list.
 * @param campaign - The campaign to resume.
 * @returns A promise resolving once the list refreshed.
 */
async function resumeCampaign(campaign: CampaignResponse): Promise<void> {
  openMenuId.value = null
  try {
    await CampaignService.resume(campaign.id)
    toast.success(`« ${campaign.name} » reprise`)
    await reload()
  } catch {
    toast.error('Échec de la reprise')
  }
}

/**
 * Open the edit drawer for a campaign (fetches its full detail first).
 * @param campaign - The campaign to edit.
 * @returns A promise resolving once the drawer opened.
 */
async function editCampaign(campaign: CampaignResponse): Promise<void> {
  openMenuId.value = null
  try {
    const detail: CampaignDetailResponse = await campaignsStore.fetchCampaign(campaign.id)
    drawerStack.push({ kind: 'campaign-form', mode: 'edit', campaign: detail })
  } catch {
    toast.error("Impossible d'ouvrir la campagne")
  }
}

/**
 * Ask confirmation before deleting a campaign.
 * @param campaign - The campaign to delete.
 */
function askDelete(campaign: CampaignResponse): void {
  openMenuId.value = null
  campaignPendingDelete.value = campaign
  deleteModal.value?.open()
}

/**
 * Delete the campaign awaiting confirmation.
 * @returns A promise resolving once deleted.
 */
async function confirmDelete(): Promise<void> {
  const campaign: CampaignResponse | null = campaignPendingDelete.value
  if (!campaign) return
  try {
    await campaignsStore.deleteCampaign(campaign.id)
    // Les stats se rechargent via le watcher sur campaignsCount (la campagne a quitté la liste).
    toast.success(`« ${campaign.name} » supprimée`)
  } catch {
    toast.error('Échec de la suppression')
  } finally {
    campaignPendingDelete.value = null
  }
}

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
        stats: await CampaignService.getStats(campaign.id).catch((): null => null),
      }),
    ),
  )
  const map: Record<number, CampaignStats | null> = {}
  for (const result of results) map[result.id] = result.stats
  statsById.value = map
}

/** localStorage key persisting the campaigns period filter across visits. */
const PERIOD_STORAGE_KEY: string = 'dlh:campaigns:period'

/** Every valid period preset, used to validate a persisted value. */
const PERIOD_PRESETS: PeriodPreset[] = ['all', 'week', 'month', '30d', 'custom']

/**
 * Restore the persisted period filter from localStorage (client only).
 * @returns The stored period, or null when nothing valid is stored.
 */
function loadStoredPeriod(): PeriodValue | null {
  if (import.meta.server) return null
  const raw: string | null = localStorage.getItem(PERIOD_STORAGE_KEY)
  if (!raw) return null
  try {
    const parsed: PeriodValue = JSON.parse(raw) as PeriodValue
    if (!PERIOD_PRESETS.includes(parsed.preset)) return null
    if (parsed.preset === 'custom' && (!parsed.start || !parsed.end)) return null
    return { preset: parsed.preset, start: parsed.start ?? null, end: parsed.end ?? null }
  } catch {
    return null
  }
}

/**
 * Persist the active period filter to localStorage (client only).
 * @param value - The period to store.
 */
function storePeriod(value: PeriodValue): void {
  if (import.meta.server) return
  localStorage.setItem(PERIOD_STORAGE_KEY, JSON.stringify(value))
}

/**
 * Read the initial filter state from the URL query so a refresh or back navigation restores the view.
 * @returns Whether the URL pinned an explicit status tab.
 */
function initFiltersFromQuery(): boolean {
  const query: LocationQuery = route.query
  if (query.view === 'forecast') view.value = 'forecast'
  if (typeof query.q === 'string') searchQuery.value = query.q
  const sortKeys: CampaignSortKey[] = SORT_OPTIONS.map((option: SortOption): CampaignSortKey => option.key)
  if (typeof query.sort === 'string' && sortKeys.includes(query.sort as CampaignSortKey)) {
    sortKey.value = query.sort as CampaignSortKey
  }
  if (typeof query.period === 'string') {
    if (query.period === 'week' || query.period === 'month' || query.period === '30d') {
      period.value = { preset: query.period, start: null, end: null }
    } else if (query.period === 'custom' && typeof query.from === 'string' && typeof query.to === 'string') {
      period.value = { preset: 'custom', start: query.from, end: query.to }
    }
  } else {
    const storedPeriod: PeriodValue | null = loadStoredPeriod()
    if (storedPeriod) period.value = storedPeriod
  }
  const tabKeys: StatusTabKey[] = Object.keys(TAB_LABELS) as StatusTabKey[]
  if (typeof query.status === 'string' && tabKeys.includes(query.status as StatusTabKey)) {
    statusTab.value = query.status as StatusTabKey
    return true
  }
  return false
}

/**
 * Open on « En cours », or the first non-empty tab when it is empty, so the page never lands empty.
 */
function applyDefaultTab(): void {
  if (tabCounts.value.ongoing > 0) return
  const fallback: StatusTabKey[] = ['draft', 'done']
  statusTab.value = fallback.find((key: StatusTabKey): boolean => tabCounts.value[key] > 0) ?? 'all'
}

// Refléter les filtres dans l'URL (replace : pas d'entrée d'historique par frappe).
watch(
  [view, searchQuery, statusTab, sortKey, period],
  (): void => {
    const query: Record<string, string> = {}
    if (view.value !== 'list') query.view = view.value
    if (searchQuery.value.trim()) query.q = searchQuery.value.trim()
    if (statusTab.value !== 'ongoing') query.status = statusTab.value
    if (sortKey.value !== 'recent') query.sort = sortKey.value
    if (period.value.preset !== 'all') {
      query.period = period.value.preset
      if (period.value.preset === 'custom' && period.value.start && period.value.end) {
        query.from = period.value.start
        query.to = period.value.end
      }
    }
    void router.replace({ query })
  },
  { deep: true },
)

// Garder la période choisie d'une visite à l'autre : le filtre ne se réinitialise plus.
watch(
  period,
  (value: PeriodValue): void => {
    storePeriod(value)
  },
  { deep: true },
)

// Recharger quand une campagne est créée ou éditée depuis un drawer.
watch(
  (): number => drawerStack.campaignsRefreshCounter,
  (): void => {
    void reload()
  },
)

// Recharger les stats quand la liste change (création, suppression, refetch…).
watch(
  (): number => campaignsStore.campaignsCount,
  (): void => {
    void loadStats()
  },
)

onMounted(async (): Promise<void> => {
  const statusPinned: boolean = initFiltersFromQuery()
  await campaignsStore.fetchCampaigns()
  await loadStats()
  if (!statusPinned) applyDefaultTab()
})
</script>
