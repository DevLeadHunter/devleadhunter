<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Administration
        </p>
        <h1 class="app-page-title mt-2">Monitoring</h1>
        <p class="text-muted mt-1 text-sm">
          Le journal complet du logiciel — chaque action (mail, SMS, démo, vente, scraping, erreur…) apparaît ici, en
          temps réel.
        </p>
      </div>
      <button type="button" class="btn-secondary h-9 shrink-0 px-3 text-xs" :disabled="isLoading" @click="reloadAll">
        <UIcon name="i-lucide-refresh-cw" :class="['mr-1.5 h-3.5 w-3.5', isLoading ? 'animate-spin' : '']" />
        Rafraîchir
      </button>
    </div>

    <div
      v-if="error"
      class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-sm text-[var(--app-red)]"
    >
      {{ error }}
    </div>

    <div v-if="overview" class="grid grid-cols-2 gap-3 @xl:grid-cols-4">
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Base de données</p>
        <p class="mt-1 flex items-center gap-2 text-sm font-semibold">
          <span
            class="h-2 w-2 rounded-full"
            :style="{ backgroundColor: overview.database === 'healthy' ? 'var(--app-green)' : 'var(--app-red)' }"
          ></span>
          <span :style="{ color: overview.database === 'healthy' ? 'var(--app-green)' : 'var(--app-red)' }">
            {{ overview.database === 'healthy' ? 'Opérationnelle' : 'En panne' }}
          </span>
        </p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Sources actives (24 h)</p>
        <p class="mt-1 text-sm font-semibold text-[var(--app-ink)] tabular-nums">{{ overview.sources.length }}</p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Incidents scraping (24 h)</p>
        <p
          class="mt-1 text-sm font-semibold tabular-nums"
          :style="{ color: totalIncidents24h > 0 ? 'var(--app-red)' : 'var(--app-green)' }"
        >
          {{ totalIncidents24h }}
        </p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Actions loguées</p>
        <p class="mt-1 text-sm font-semibold text-[var(--app-ink)] tabular-nums">{{ overview.activity_total }}</p>
      </div>
    </div>

    <section v-if="overview">
      <h2 class="mb-3 text-sm font-semibold text-[var(--app-ink)]">Santé par source</h2>
      <div
        v-if="overview.sources.length === 0"
        class="text-muted rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-6 text-center text-sm"
      >
        Aucune exécution de scraping ces dernières 24 h.
      </div>
      <div v-else class="grid grid-cols-2 gap-3 @4xl:grid-cols-4">
        <div
          v-for="s in overview.sources"
          :key="s.source"
          class="rounded-lg border bg-[var(--app-surface)] px-4 py-3"
          :style="{ borderColor: scraperStatusColor(s.latest_status) }"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-[var(--app-ink)]">{{ sourceLabel(s.source) }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
              :style="{
                color: scraperStatusColor(s.latest_status),
                backgroundColor: scraperStatusSoft(s.latest_status),
              }"
            >
              {{ scraperStatusLabel(s.latest_status) }}
            </span>
          </div>
          <dl class="text-muted mt-3 space-y-1 text-xs">
            <div class="flex justify-between">
              <dt>Exécutions 24 h</dt>
              <dd class="text-[var(--app-ink)] tabular-nums">{{ s.runs_24h }}</dd>
            </div>
            <div class="flex justify-between">
              <dt>Incidents 24 h</dt>
              <dd class="tabular-nums" :style="{ color: s.incidents_24h > 0 ? 'var(--app-red)' : 'var(--app-ink)' }">
                {{ s.incidents_24h }}
              </dd>
            </div>
            <div class="flex justify-between">
              <dt>Dernier OK</dt>
              <dd class="text-[var(--app-ink)] tabular-nums">
                {{ s.last_ok_at ? formatNumericDayMonthTime(s.last_ok_at) : '—' }}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </section>

    <section>
      <h2 class="mb-3 text-sm font-semibold text-[var(--app-ink)]">Journal d'activité</h2>

      <!-- Barre d'outils : recherche à gauche, filtres statut + catégorie à droite (comme la page Sites démo). -->
      <div class="mb-4 flex flex-col gap-3 @2xl:flex-row @2xl:items-center @2xl:justify-between">
        <div class="relative w-full @2xl:max-w-xs">
          <UIcon
            name="i-lucide-search"
            class="pointer-events-none absolute top-1/2 left-3 h-3.5 w-3.5 -translate-y-1/2 text-[var(--app-faint)]"
          />
          <input
            v-model="searchQuery"
            type="search"
            placeholder="Rechercher une action, un prospect…"
            aria-label="Rechercher dans le journal"
            class="app-input pl-9"
          />
        </div>
        <div class="flex flex-col gap-3 @sm:flex-row @2xl:items-center">
          <div class="w-full @sm:w-44">
            <UiSelectField v-model="selectedStatus" :options="statusFilterOptions" aria-label="Filtrer par statut" />
          </div>
          <div class="w-full @sm:w-52">
            <UiSelectField
              v-model="selectedCategory"
              :options="categoryFilterOptions"
              aria-label="Filtrer par catégorie"
            />
          </div>
        </div>
      </div>

      <div class="app-card overflow-hidden p-0">
        <BaseTable>
          <template #head>
            <BaseTableTh>Date</BaseTableTh>
            <BaseTableTh>Catégorie</BaseTableTh>
            <BaseTableTh>Statut</BaseTableTh>
            <BaseTableTh>Action</BaseTableTh>
            <BaseTableTh>Détail</BaseTableTh>
          </template>

          <BaseTableTr v-if="isLoadingActivity">
            <BaseTableTd colspan="5" class="py-8 text-center">
              <UIcon name="i-lucide-loader-circle" class="mx-auto h-5 w-5 animate-spin text-[var(--app-ink-soft)]" />
            </BaseTableTd>
          </BaseTableTr>

          <BaseTableTr v-else-if="entries.length === 0">
            <BaseTableTd colspan="5" class="py-8 text-center text-sm text-[var(--app-ink-soft)]">
              {{ hasActiveFilters ? 'Aucune action ne correspond à ces filtres.' : 'Aucune action enregistrée.' }}
            </BaseTableTd>
          </BaseTableTr>

          <BaseTableTr v-for="entry in entries" v-else :key="entry.id">
            <BaseTableTd class="font-label text-xs whitespace-nowrap text-[var(--app-ink-soft)] tabular-nums">
              {{ entry.created_at ? formatNumericDayMonthTime(entry.created_at) : '—' }}
            </BaseTableTd>
            <BaseTableTd label="Catégorie" class="text-sm font-semibold text-[var(--app-ink)]">
              {{ categoryLabel(entry.category) }}
            </BaseTableTd>
            <BaseTableTd label="Statut">
              <span
                class="app-badge"
                :style="{ color: feedStatusColor(entry.status), backgroundColor: feedStatusSoft(entry.status) }"
              >
                {{ feedStatusLabel(entry.status) }}
              </span>
            </BaseTableTd>
            <BaseTableTd label="Action" class="text-sm text-[var(--app-ink)]">
              <NuxtLink
                v-if="entryLink(entry)"
                :to="entryLink(entry) ?? ''"
                class="hover:text-[var(--app-accent-ink)] hover:underline"
              >
                {{ entry.title }}
              </NuxtLink>
              <span v-else>{{ entry.title }}</span>
            </BaseTableTd>
            <BaseTableTd label="Détail">
              <button
                v-if="entry.entity_type === 'scraper_diagnostic' && entry.entity_id"
                type="button"
                class="cursor-pointer text-xs font-medium text-[var(--app-accent-ink)] underline-offset-2 hover:underline"
                @click="openHtml(entry.entity_id, entry.title)"
              >
                Voir le HTML
              </button>
              <span
                v-else-if="entry.detail"
                class="block max-w-[280px] truncate text-xs text-[var(--app-ink-soft)]"
                :title="entry.detail"
              >
                {{ entry.detail }}
              </span>
              <span v-else class="text-sm text-[var(--app-faint)]">—</span>
            </BaseTableTd>
          </BaseTableTr>
        </BaseTable>
      </div>
    </section>

    <Teleport to="body">
      <Transition name="drawer-panel">
        <div
          v-if="htmlPanel.open"
          class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[720px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
        >
          <div class="flex items-center justify-between border-b border-[var(--app-line)] px-5 py-4">
            <div class="min-w-0">
              <h2 class="truncate text-sm font-semibold text-[var(--app-ink)]">
                HTML capturé — {{ htmlPanel.source }}
              </h2>
              <p class="text-muted mt-0.5 truncate text-[11px]">
                Markup brut au moment du blocage — pour écrire le nouveau sélecteur.
              </p>
            </div>
            <button
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
              @click="htmlPanel.open = false"
            >
              <UIcon name="i-lucide-x" class="h-4 w-4" />
            </button>
          </div>
          <div class="flex-1 overflow-auto p-4">
            <div v-if="htmlPanel.loading" class="flex h-40 items-center justify-center">
              <UIcon name="i-lucide-loader-circle" class="h-6 w-6 animate-spin text-[var(--app-ink-soft)]" />
            </div>
            <pre
              v-else
              class="font-label rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3 text-[11px] leading-relaxed break-words whitespace-pre-wrap text-[var(--app-ink-soft)]"
              >{{ htmlPanel.content }}</pre
            >
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script lang="ts" setup>
import { formatNumericDayMonthTime } from '~/utils/date'
import type { UseToastReturn } from '~/types/Composables'
import type { HtmlPanelState } from '~/types/AdminMonitoringPage'
import type { SelectFieldOption } from '~/types/SelectField'
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'
import type {
  ActivityLogEntry,
  ActivityLogResponse,
  MonitoringOverview,
  ScraperSourceHealth,
} from '~/services/adminMonitoringService'
import { AdminMonitoringService } from '~/services/adminMonitoringService'
import { isPlatformAdmin } from '~/utils/userRoles'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth', 'admin'],
})

const userStore: ReturnType<typeof useUserStore> = useUserStore()
const toast: UseToastReturn = useToast()
const router: ReturnType<typeof useRouter> = useRouter()

// The « all » sentinel value both selects use when no filter is applied.
const ALL_FILTER_VALUE: string = 'all'
// Debounce the free-text search so typing does not fire a request per keystroke.
const SEARCH_DEBOUNCE_MS: number = 300

const isLoading: Ref<boolean> = ref(false)
const isLoadingActivity: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)
const overview: Ref<MonitoringOverview | null> = ref(null)
const entries: Ref<ActivityLogEntry[]> = ref([])
const availableCategories: Ref<string[]> = ref([])

const searchQuery: Ref<string> = ref('')
const selectedStatus: Ref<string> = ref(ALL_FILTER_VALUE)
const selectedCategory: Ref<string> = ref(ALL_FILTER_VALUE)
let searchDebounceTimer: ReturnType<typeof setTimeout> | null = null

const htmlPanel: Ref<HtmlPanelState> = ref({
  open: false,
  loading: false,
  source: '',
  content: '',
})

/** Total scraping incidents across all sources over the last 24 h. */
const totalIncidents24h: ComputedRef<number> = computed((): number =>
  (overview.value?.sources ?? []).reduce((sum: number, s: ScraperSourceHealth): number => sum + s.incidents_24h, 0),
)

/** Options for the status filter (outcome levels of the feed). */
const statusFilterOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] => [
  { value: ALL_FILTER_VALUE, label: 'Tous les statuts' },
  { value: 'error', label: 'Erreurs' },
  { value: 'warning', label: 'Alertes' },
  { value: 'success', label: 'Succès' },
  { value: 'pending', label: 'En attente' },
  { value: 'info', label: 'Infos' },
])

/** Options for the category filter, built from the categories present in the feed. */
const categoryFilterOptions: ComputedRef<SelectFieldOption[]> = computed((): SelectFieldOption[] => [
  { value: ALL_FILTER_VALUE, label: 'Toutes les catégories' },
  ...availableCategories.value.map(
    (category: string): SelectFieldOption => ({
      value: category,
      label: categoryLabel(category),
    }),
  ),
])

/** Whether any filter narrows the feed. */
const hasActiveFilters: ComputedRef<boolean> = computed(
  (): boolean =>
    searchQuery.value.trim() !== '' ||
    selectedStatus.value !== ALL_FILTER_VALUE ||
    selectedCategory.value !== ALL_FILTER_VALUE,
)

/**
 * Human label for an activity category.
 * @param category - Raw category key.
 * @returns The French label (falls back to a capitalized key).
 */
function categoryLabel(category: string): string {
  const labels: Record<string, string> = {
    email: 'E-mail',
    sms: 'SMS',
    demo: 'Démo',
    assistant: 'Réceptionniste IA',
    sale: 'Vente',
    prospect: 'Prospect',
    demo_site: 'Site démo',
    campaign: 'Campagne',
    scraping: 'Scraping',
    auth: 'Connexion',
    system: 'Système',
  }
  return labels[category] ?? category.charAt(0).toUpperCase() + category.slice(1)
}

/**
 * Accent colour for a feed outcome status.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function feedStatusColor(status: string): string {
  if (status === 'success') return 'var(--app-green)'
  if (status === 'error') return 'var(--app-red)'
  if (status === 'info') return 'var(--app-ink-soft)'
  return 'var(--app-accent)' // warning / pending
}

/**
 * Soft background colour for a feed status badge.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function feedStatusSoft(status: string): string {
  if (status === 'success') return 'var(--app-green-soft)'
  if (status === 'error') return 'var(--app-red-soft)'
  if (status === 'info') return 'var(--app-surface-2)'
  return 'var(--app-accent-soft)' // warning / pending
}

/**
 * Human label for a feed status.
 * @param status - Outcome status.
 * @returns The French label.
 */
function feedStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    success: 'Succès',
    error: 'Erreur',
    warning: 'Alerte',
    pending: 'En attente',
    info: 'Info',
  }
  return labels[status] ?? status
}

/**
 * Deep link to the resource an entry is about, when it is navigable.
 * @param entry - The activity entry.
 * @returns The in-app path, or ``null`` when there is no navigable resource.
 */
function entryLink(entry: ActivityLogEntry): string | null {
  if (!entry.entity_id) return null
  if (entry.entity_type === 'prospect') return `/dashboard/my-prospects?open=${entry.entity_id}`
  if (entry.entity_type === 'demo_site') return `/dashboard/demo-sites/${entry.entity_id}`
  if (entry.entity_type === 'order') return `/dashboard/orders?open=${entry.entity_id}`
  if (entry.entity_type === 'campaign') return `/dashboard/campaigns/${entry.entity_id}`
  return null
}

/**
 * Human label for a diagnostics source (scrapers + enrichment steps).
 * @param source - Raw source key recorded with each run.
 * @returns The French label (falls back to a capitalized key).
 */
function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    google: 'Google',
    pagesjaunes: 'Pages Jaunes',
    osm: 'OpenStreetMap',
    brightdata: 'Bright Data',
    facebook: 'Facebook',
    auto: 'Recherche auto',
    yelp: 'Yelp',
    enrichment: 'Enrichissement',
    decision_maker: 'Nom du décisionnaire',
  }
  return labels[source] ?? source.charAt(0).toUpperCase() + source.slice(1)
}

/**
 * Accent colour for a scraper source status.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function scraperStatusColor(status: string): string {
  if (status === 'ok') return 'var(--app-green)'
  if (status === 'blocked' || status === 'error') return 'var(--app-red)'
  return 'var(--app-accent)' // empty / timeout
}

/**
 * Soft background colour for a scraper status badge.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function scraperStatusSoft(status: string): string {
  if (status === 'ok') return 'var(--app-green-soft)'
  if (status === 'blocked' || status === 'error') return 'var(--app-red-soft)'
  return 'var(--app-accent-soft)'
}

/**
 * Human label for a scraper source status.
 * @param status - Outcome status.
 * @returns The French label.
 */
function scraperStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: 'OK',
    empty: 'Vide',
    blocked: 'Bloqué',
    timeout: 'Timeout',
    error: 'Erreur',
  }
  return labels[status] ?? status
}

/**
 * Load the health overview (system + per-source scraping).
 * @returns A promise resolved once loaded.
 */
async function loadOverview(): Promise<void> {
  try {
    overview.value = await AdminMonitoringService.getMonitoringOverview()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Impossible de charger le monitoring.'
  }
}

/**
 * Load the activity feed with the active filters applied.
 * @returns A promise resolved once loaded.
 */
async function loadActivity(): Promise<void> {
  isLoadingActivity.value = true
  try {
    const response: ActivityLogResponse = await AdminMonitoringService.getActivityLog({
      status: selectedStatus.value === ALL_FILTER_VALUE ? undefined : selectedStatus.value,
      category: selectedCategory.value === ALL_FILTER_VALUE ? undefined : selectedCategory.value,
      q: searchQuery.value,
    })
    entries.value = response.items
    // Keep the known categories growing so a filter never hides its own option.
    availableCategories.value = Array.from(new Set([...availableCategories.value, ...response.categories])).sort()
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Impossible de charger le journal.'
  } finally {
    isLoadingActivity.value = false
  }
}

/**
 * Reload both the overview and the activity feed.
 * @returns A promise resolved once both are loaded.
 */
async function reloadAll(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    await Promise.all([loadOverview(), loadActivity()])
  } finally {
    isLoading.value = false
  }
}

/**
 * Open the slide-over and fetch the captured HTML for a scraper diagnostic.
 * @param diagnosticId - The scraper diagnostic id.
 * @param label - A short label for the panel header.
 * @returns A promise resolved once the HTML is loaded.
 */
async function openHtml(diagnosticId: number, label: string): Promise<void> {
  htmlPanel.value = { open: true, loading: true, source: label, content: '' }
  try {
    htmlPanel.value.content = await AdminMonitoringService.getScraperIncidentHtml(diagnosticId)
  } catch (err) {
    htmlPanel.value.content = err instanceof Error ? err.message : 'Impossible de charger le HTML.'
  } finally {
    htmlPanel.value.loading = false
  }
}

// Status / category changes refetch immediately.
watch([selectedStatus, selectedCategory], (): void => {
  void loadActivity()
})

// The free-text search refetches after a short debounce.
watch(searchQuery, (): void => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout((): void => {
    void loadActivity()
  }, SEARCH_DEBOUNCE_MS)
})

onMounted((): void => {
  // Hidden admin page: only admins may view it.
  if (!isPlatformAdmin(userStore.user?.role)) {
    toast.error('Accès réservé aux administrateurs')
    void router.replace('/dashboard')
    return
  }
  void reloadAll()
})

onBeforeUnmount((): void => {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
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
