<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 class="text-xl font-semibold text-[var(--app-ink)]">Monitoring</h1>
        <p class="text-muted mt-1 text-sm">
          Santé du système et des sources de scraping — capturé automatiquement lors des vraies exécutions.
        </p>
      </div>
      <button type="button" class="btn-secondary h-9 shrink-0 px-3 text-xs" :disabled="isLoading" @click="load">
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

    <!-- System health -->
    <div v-if="overview" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
        <p class="text-muted text-[10px] tracking-wide uppercase">Incidents (24 h)</p>
        <p
          class="mt-1 text-sm font-semibold tabular-nums"
          :style="{ color: totalIncidents24h > 0 ? 'var(--app-red)' : 'var(--app-green)' }"
        >
          {{ totalIncidents24h }}
        </p>
      </div>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3">
        <p class="text-muted text-[10px] tracking-wide uppercase">Diagnostics stockés</p>
        <p class="mt-1 text-sm font-semibold text-[var(--app-ink)] tabular-nums">{{ overview.diagnostics_total }}</p>
      </div>
    </div>

    <!-- Per-source health -->
    <section v-if="overview">
      <h2 class="mb-3 text-sm font-semibold text-[var(--app-ink)]">Santé par source</h2>
      <div
        v-if="overview.sources.length === 0"
        class="text-muted rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-6 text-center text-sm"
      >
        Aucune exécution de scraping ces dernières 24 h.
      </div>
      <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div
          v-for="s in overview.sources"
          :key="s.source"
          class="rounded-lg border bg-[var(--app-surface)] px-4 py-3"
          :style="{ borderColor: statusColor(s.latest_status) }"
        >
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-[var(--app-ink)]">{{ sourceLabel(s.source) }}</span>
            <span
              class="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
              :style="{ color: statusColor(s.latest_status), backgroundColor: statusSoft(s.latest_status) }"
            >
              {{ statusLabel(s.latest_status) }}
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
              <dd class="text-[var(--app-ink)] tabular-nums">{{ s.last_ok_at ? formatDate(s.last_ok_at) : '—' }}</dd>
            </div>
          </dl>
        </div>
      </div>
    </section>

    <!-- Incidents -->
    <section>
      <h2 class="mb-3 text-sm font-semibold text-[var(--app-ink)]">Journal des exécutions</h2>
      <div class="overflow-x-auto rounded-lg border border-[var(--app-line)]">
        <table class="w-full min-w-[720px] text-sm">
          <thead>
            <tr class="border-b border-[var(--app-line)] bg-[var(--app-bg)] text-left">
              <th class="text-muted px-3 py-2 text-[10px] font-medium tracking-wide uppercase">Date</th>
              <th class="text-muted px-3 py-2 text-[10px] font-medium tracking-wide uppercase">Source</th>
              <th class="text-muted px-3 py-2 text-[10px] font-medium tracking-wide uppercase">Statut</th>
              <th class="text-muted px-3 py-2 text-[10px] font-medium tracking-wide uppercase">Recherche</th>
              <th class="text-muted px-3 py-2 text-right text-[10px] font-medium tracking-wide uppercase">Résultats</th>
              <th class="text-muted px-3 py-2 text-[10px] font-medium tracking-wide uppercase">Détail</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="incidents.length === 0">
              <td colspan="6" class="text-muted px-3 py-6 text-center">Aucune exécution enregistrée.</td>
            </tr>
            <tr
              v-for="incident in incidents"
              :key="incident.id"
              class="border-b border-[var(--app-line-soft)] last:border-b-0"
            >
              <td class="text-muted px-3 py-2 whitespace-nowrap tabular-nums">
                {{ incident.created_at ? formatDate(incident.created_at) : '—' }}
              </td>
              <td class="px-3 py-2 font-medium text-[var(--app-ink)]">{{ sourceLabel(incident.source) }}</td>
              <td class="px-3 py-2">
                <span
                  class="rounded-full px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
                  :style="{ color: statusColor(incident.status), backgroundColor: statusSoft(incident.status) }"
                >
                  {{ statusLabel(incident.status) }}
                </span>
              </td>
              <td class="text-muted px-3 py-2">
                <span v-if="incident.category || incident.city">{{
                  [incident.category, incident.city].filter(Boolean).join(' · ')
                }}</span>
                <span v-else>—</span>
              </td>
              <td class="px-3 py-2 text-right text-[var(--app-ink)] tabular-nums">
                {{ incident.results_count
                }}<span v-if="incident.expected_count" class="text-[var(--app-faint)]">
                  / {{ incident.expected_count }}</span
                >
              </td>
              <td class="px-3 py-2">
                <button
                  v-if="incident.has_html"
                  type="button"
                  class="text-xs font-medium text-[var(--app-blue)] underline underline-offset-2 hover:opacity-80"
                  @click="openHtml(incident)"
                >
                  Voir le HTML
                </button>
                <span
                  v-else-if="incident.error_message"
                  class="text-muted truncate text-xs"
                  :title="incident.error_message"
                >
                  {{ incident.error_message }}
                </span>
                <span v-else class="text-xs text-[var(--app-faint)]">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Captured-HTML slide-over -->
    <Teleport to="body">
      <Transition name="drawer-panel">
        <div
          v-if="htmlPanel.open"
          class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[720px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
        >
          <div class="flex items-center justify-between border-b border-[var(--app-line)] px-5 py-4">
            <div class="min-w-0">
              <h2 class="text-sm font-semibold text-[var(--app-ink)]">HTML capturé — {{ htmlPanel.source }}</h2>
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
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import { useUserStore } from '~/stores/user'
import { useToast } from '~/composables/useToast'
import type { MonitoringOverview, ScraperIncident } from '~/services/adminMonitoringService'
import { getMonitoringOverview, getScraperIncidents, getScraperIncidentHtml } from '~/services/adminMonitoringService'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

/** State of the captured-HTML slide-over. */
interface HtmlPanelState {
  open: boolean
  loading: boolean
  source: string
  content: string
}

const userStore = useUserStore()
const toast = useToast()
const router = useRouter()

const isLoading: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)
const overview: Ref<MonitoringOverview | null> = ref(null)
const incidents: Ref<ScraperIncident[]> = ref([])
const htmlPanel: Ref<HtmlPanelState> = ref({
  open: false,
  loading: false,
  source: '',
  content: '',
})

/** Total incidents across all sources over the last 24 h. */
const totalIncidents24h: ComputedRef<number> = computed((): number =>
  (overview.value?.sources ?? []).reduce((sum: number, s): number => sum + s.incidents_24h, 0),
)

/**
 * Resolve the accent colour for a source/run status.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function statusColor(status: string): string {
  if (status === 'ok') return 'var(--app-green)'
  if (status === 'blocked' || status === 'error') return 'var(--app-red)'
  return 'var(--app-accent)' // empty / timeout
}

/**
 * Resolve the soft background colour for a status badge.
 * @param status - Outcome status.
 * @returns A CSS colour variable.
 */
function statusSoft(status: string): string {
  if (status === 'ok') return 'var(--app-green-soft)'
  if (status === 'blocked' || status === 'error') return 'var(--app-red-soft)'
  return 'var(--app-accent-soft)'
}

/**
 * Human label for a status.
 * @param status - Outcome status.
 * @returns The French label.
 */
function statusLabel(status: string): string {
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
    auto: 'Recherche auto',
    yelp: 'Yelp',
    enrichment: 'Enrichissement',
    decision_maker: 'Nom du décisionnaire',
  }
  return labels[source] ?? source.charAt(0).toUpperCase() + source.slice(1)
}

/**
 * Format an ISO timestamp for display.
 * @param iso - ISO 8601 string.
 * @returns A locale date-time string.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Load the monitoring overview and the recent incidents.
 * @returns A promise resolved once loaded.
 */
async function load(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    const [overviewData, incidentsData] = await Promise.all([getMonitoringOverview(), getScraperIncidents(100)])
    overview.value = overviewData
    incidents.value = incidentsData.items
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Impossible de charger le monitoring.'
  } finally {
    isLoading.value = false
  }
}

/**
 * Open the slide-over and fetch the captured HTML for an incident.
 * @param incident - The incident to inspect.
 * @returns A promise resolved once the HTML is loaded.
 */
async function openHtml(incident: ScraperIncident): Promise<void> {
  htmlPanel.value = { open: true, loading: true, source: incident.source, content: '' }
  try {
    htmlPanel.value.content = await getScraperIncidentHtml(incident.id)
  } catch (err) {
    htmlPanel.value.content = err instanceof Error ? err.message : 'Impossible de charger le HTML.'
  } finally {
    htmlPanel.value.loading = false
  }
}

onMounted((): void => {
  // Hidden admin page: only admins may view it.
  if (userStore.user?.role !== 'ADMIN') {
    toast.error('Accès réservé aux administrateurs')
    void router.replace('/dashboard')
    return
  }
  void load()
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
