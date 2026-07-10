<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 class="text-2xl font-bold text-[var(--app-ink)]">Tableau de bord</h1>
        <p class="text-muted mt-1 text-sm">Vue d'ensemble de votre tunnel, de la prospection à la vente</p>
      </div>
      <div class="flex items-center gap-3">
        <span v-if="lastUpdated" class="text-muted hidden text-xs sm:inline">Mis à jour à {{ lastUpdated }}</span>
        <button type="button" class="btn-secondary h-9 px-3 text-xs" :disabled="isLoading" @click="load">
          <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
      </div>
    </div>

    <!-- Loading skeleton -->
    <div v-if="isLoading && !stats" class="space-y-6">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="n in 4" :key="n" class="card h-28 animate-pulse">
          <div class="h-10 w-10 rounded-lg bg-[var(--app-surface-2)]"></div>
          <div class="mt-4 h-6 w-2/3 rounded bg-[var(--app-surface-2)]"></div>
        </div>
      </div>
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="card h-80 animate-pulse lg:col-span-2"></div>
        <div class="card h-80 animate-pulse"></div>
      </div>
    </div>

    <template v-else-if="stats">
      <!-- KPI row -->
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <DashboardKpiCard
          label="Prospects"
          :value="formatInt(stats.prospects_total)"
          icon="i-lucide-users"
          accent="blue"
          :hint="`${stats.demo_sites_active} avec démo active`"
          to="/dashboard/my-prospects"
        />
        <DashboardKpiCard
          label="Démos actives"
          :value="formatInt(stats.demo_sites_active)"
          icon="i-lucide-app-window"
          accent="violet"
          hint="En ligne sur demo.dibodev.fr"
          to="/dashboard/demo-sites"
        />
        <DashboardKpiCard
          label="Campagnes actives"
          :value="formatInt(stats.campaigns_active)"
          icon="i-lucide-megaphone"
          accent="amber"
          :hint="`${formatInt(stats.emails_sent)} emails envoyés`"
          to="/dashboard/campaigns"
        />
        <DashboardKpiCard
          label="Chiffre d'affaires"
          :value="formatCents(stats.revenue_cents)"
          icon="i-lucide-banknote"
          accent="green"
          :hint="`${stats.sales_won} vente${stats.sales_won > 1 ? 's' : ''} · pipeline ${formatCents(stats.pipeline_cents)}`"
          to="/dashboard/orders"
        />
      </div>

      <!-- Hot leads — the actionable section comes first -->
      <section class="card">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="flex items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
            <UIcon name="i-lucide-flame" class="h-4 w-4 text-[var(--app-red)]" /> Leads chauds
            <span v-if="hotLeads.length" class="text-muted font-normal">({{ hotLeads.length }})</span>
          </h2>
          <NuxtLink to="/dashboard/my-prospects" class="text-xs text-[var(--app-accent-ink)] hover:underline">
            Tous les prospects →
          </NuxtLink>
        </div>

        <div v-if="hotLeads.length" class="grid grid-cols-1 gap-2 md:grid-cols-2">
          <button
            v-for="lead in displayedHotLeads"
            :key="lead.prospect_id"
            type="button"
            class="flex w-full items-center gap-3 rounded-lg border border-[var(--app-surface-2)] p-3 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)] hover:bg-[var(--app-surface-2)]"
            @click="openProspect(lead.prospect_id)"
          >
            <span
              class="inline-flex flex-shrink-0 items-center gap-1 rounded px-2 py-0.5 text-[10px] font-semibold"
              :class="temperatureClass(lead.temperature)"
            >
              <span class="h-1.5 w-1.5 rounded-full bg-current"></span>{{ temperatureLabel(lead.temperature) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ lead.name }}</p>
              <p class="text-muted truncate text-xs">
                {{ lead.city || '—' }}<span v-if="lead.last_seen"> · vu {{ formatDate(lead.last_seen) }}</span>
              </p>
            </div>
            <div class="flex flex-shrink-0 items-center gap-2">
              <div class="w-16">
                <div class="h-1.5 overflow-hidden rounded-full bg-[var(--app-surface)]">
                  <div class="h-full rounded-full" :style="scoreBarStyle(lead.score)"></div>
                </div>
              </div>
              <span class="w-10 text-right text-sm font-bold text-[var(--app-ink)] tabular-nums">{{ lead.score }}</span>
              <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
            </div>
          </button>
        </div>

        <div v-else class="flex flex-col items-center gap-2 py-6 text-center">
          <UIcon name="i-lucide-snowflake" class="h-7 w-7 text-[var(--app-faint)]" />
          <p class="text-muted text-sm">Aucun lead chaud pour l'instant.</p>
          <p class="text-xs text-[var(--app-ink-soft)]">
            Les prospects qui ouvrent vos emails et visitent leur démo apparaîtront ici.
          </p>
        </div>
      </section>

      <!-- Detail — one theme at a time (tunnel / emails / ventes) -->
      <section class="card">
        <div class="mb-5 border-b border-[var(--app-line)]">
          <nav class="flex gap-1">
            <button
              v-for="tab in DETAIL_TABS"
              :key="tab.key"
              type="button"
              :class="[
                '-mb-px flex cursor-pointer items-center gap-2 border-b-2 px-3 pt-1 pb-2.5 text-sm font-medium transition-colors',
                activeDetailTab === tab.key
                  ? 'border-[var(--app-ink)] text-[var(--app-ink)]'
                  : 'border-transparent text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]',
              ]"
              @click="activeDetailTab = tab.key"
            >
              <UIcon :name="tab.icon" class="h-4 w-4" />
              {{ tab.label }}
            </button>
          </nav>
        </div>

        <!-- Tunnel de conversion -->
        <div v-if="activeDetailTab === 'funnel'">
          <div class="mb-4 flex items-center justify-between">
            <p class="text-muted text-xs">De la prospection à la vente, sur l'ensemble de votre activité.</p>
            <span class="text-muted text-xs">{{ funnelTopToBottom }}</span>
          </div>
          <DashboardConversionFunnel :stages="funnelStages" />
        </div>

        <!-- Emails : engagement + activité -->
        <div v-else-if="activeDetailTab === 'emails'" class="space-y-6">
          <div class="grid grid-cols-1 gap-6 lg:grid-cols-[auto_1fr]">
            <div class="flex items-center gap-8 lg:pr-6">
              <DashboardRadialRate
                :value="stats.open_rate"
                label="Taux d'ouverture"
                accent="blue"
                :sublabel="`${formatInt(stats.emails_opened)} / ${formatInt(stats.emails_sent)}`"
              />
              <DashboardRadialRate
                :value="stats.click_rate"
                label="Taux de clic"
                accent="green"
                :sublabel="`${formatInt(stats.emails_clicked)} / ${formatInt(stats.emails_sent)}`"
              />
            </div>
            <div
              class="grid grid-cols-3 items-center gap-2 border-t border-[var(--app-surface-2)] pt-4 text-center lg:border-t-0 lg:border-l lg:pt-0 lg:pl-6"
            >
              <div>
                <p class="text-lg font-bold text-[var(--app-ink)] tabular-nums">{{ formatInt(stats.emails_sent) }}</p>
                <p class="text-muted text-[11px]">Envoyés</p>
              </div>
              <div>
                <p class="text-lg font-bold text-[var(--app-ink)] tabular-nums">{{ formatInt(stats.emails_opened) }}</p>
                <p class="text-muted text-[11px]">Ouverts</p>
              </div>
              <div>
                <p class="text-lg font-bold text-[var(--app-ink)] tabular-nums">
                  {{ formatInt(stats.emails_clicked) }}
                </p>
                <p class="text-muted text-[11px]">Cliqués</p>
              </div>
            </div>
          </div>

          <div>
            <div class="mb-1 flex items-center justify-between">
              <h3 class="text-sm font-semibold text-[var(--app-ink)]">Activité — 14 derniers jours</h3>
              <NuxtLink to="/dashboard/emails" class="text-xs text-[var(--app-accent-ink)] hover:underline"
                >Suivi des emails →</NuxtLink
              >
            </div>
            <DashboardActivityChart v-if="activity.length" :points="activity" />
            <p v-else class="text-muted py-10 text-center text-sm">Aucune activité email sur la période.</p>
          </div>
        </div>

        <!-- Ventes -->
        <div v-else class="grid grid-cols-1 gap-6 md:grid-cols-2">
          <div>
            <p class="text-3xl font-bold text-[var(--app-green)] tabular-nums">
              {{ formatCents(stats.revenue_cents) }}
            </p>
            <p class="text-muted mt-1 text-xs">Chiffre d'affaires encaissé</p>
            <NuxtLink
              to="/dashboard/orders"
              class="mt-3 inline-block text-xs text-[var(--app-accent-ink)] hover:underline"
            >
              Voir les ventes →
            </NuxtLink>
          </div>
          <div class="space-y-3">
            <div>
              <div class="mb-1 flex items-center justify-between text-xs">
                <span class="text-[var(--app-ink)]">Ventes gagnées</span>
                <span class="text-[var(--app-ink-soft)] tabular-nums"
                  >{{ stats.sales_won }} / {{ stats.orders_total }}</span
                >
              </div>
              <div class="h-2 overflow-hidden rounded-full bg-[var(--app-surface)]">
                <div
                  class="h-full rounded-full bg-[var(--app-green)] transition-all duration-700"
                  :style="{ width: `${wonRatio}%` }"
                ></div>
              </div>
            </div>
            <div class="flex items-center justify-between rounded-lg border border-[var(--app-surface-2)] px-3 py-2">
              <span class="flex items-center gap-2 text-xs text-[var(--app-ink)]">
                <UIcon name="i-lucide-hourglass" class="h-3.5 w-3.5 text-[var(--app-accent)]" /> Pipeline en cours
              </span>
              <span class="text-sm font-bold text-[var(--app-accent)] tabular-nums">{{
                formatCents(stats.pipeline_cents)
              }}</span>
            </div>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]">
      <p class="text-sm">Impossible de charger les statistiques.</p>
      <button type="button" class="btn-secondary mt-3 h-9 px-3 text-xs" @click="load">Réessayer</button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { FunnelStage } from '~/types/DashboardConversionFunnel'
import type { ActivityPoint, DashboardStats, HotLead } from '~/services/dashboardService'
import { getDashboardActivity, getDashboardStats, getHotLeads } from '~/services/dashboardService'
import { getProspect } from '~/services/prospectsService'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { hexAlpha } from '~/utils/dashboardTheme'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

/** Keys of the detail tabs (progressive disclosure of the metrics). */
type DashboardDetailTabKey = 'funnel' | 'emails' | 'sales'

/** Detail tabs shown one at a time below the KPIs. */
const DETAIL_TABS: ReadonlyArray<{ key: DashboardDetailTabKey; label: string; icon: string }> = [
  { key: 'funnel', label: 'Tunnel de conversion', icon: 'i-lucide-filter' },
  { key: 'emails', label: 'Emails', icon: 'i-lucide-mail' },
  { key: 'sales', label: 'Ventes', icon: 'i-lucide-banknote' },
]

const stats: Ref<DashboardStats | null> = ref<DashboardStats | null>(null)
const hotLeads: Ref<HotLead[]> = ref<HotLead[]>([])
const activity: Ref<ActivityPoint[]> = ref<ActivityPoint[]>([])
const isLoading: Ref<boolean> = ref(false)
const lastUpdated: Ref<string | null> = ref<string | null>(null)

/** Currently displayed detail tab. */
const activeDetailTab: Ref<DashboardDetailTabKey> = ref<DashboardDetailTabKey>('funnel')

/** Hot leads limited to the most relevant ones (the page stays breathable). */
const displayedHotLeads: ComputedRef<HotLead[]> = computed((): HotLead[] => hotLeads.value.slice(0, 6))

const TEMPERATURE_LABELS: Record<string, string> = {
  hot: 'Chaud',
  warm: 'Tiède',
  cold: 'Froid',
  unknown: 'Inconnu',
}

/** Funnel stages derived from the headline KPIs (prospect → sale). */
const funnelStages: ComputedRef<FunnelStage[]> = computed((): FunnelStage[] => {
  const s: DashboardStats | null = stats.value
  if (!s) return []
  return [
    { label: 'Prospects', value: s.prospects_total, accent: 'slate' },
    { label: 'Emails envoyés', value: s.emails_sent, accent: 'blue' },
    { label: 'Emails ouverts', value: s.emails_opened, accent: 'violet' },
    { label: 'Emails cliqués', value: s.emails_clicked, accent: 'amber' },
    { label: 'Ventes', value: s.sales_won, accent: 'green' },
  ]
})

/** Short "top → bottom" conversion label for the funnel header. */
const funnelTopToBottom: ComputedRef<string> = computed((): string => {
  const s: DashboardStats | null = stats.value
  if (!s || s.prospects_total <= 0) return ''
  const pct: number = Math.round((s.sales_won / s.prospects_total) * 100)
  return `${pct}% prospect → vente`
})

/** Share of won orders over total orders, as a percentage. */
const wonRatio: ComputedRef<number> = computed((): number => {
  const s: DashboardStats | null = stats.value
  if (!s || s.orders_total <= 0) return 0
  return Math.round((s.sales_won / s.orders_total) * 100)
})

/**
 * Format an integer with French thousands separators.
 * @param n - Number to format.
 * @returns Locale-formatted string.
 */
function formatInt(n: number): string {
  return n.toLocaleString('fr-FR')
}

/**
 * Format an amount in cents as euros.
 * @param cents - Amount in cents.
 * @returns Formatted euro string.
 */
function formatCents(cents: number): string {
  const euros: number = cents / 100
  return `${euros.toLocaleString('fr-FR', { maximumFractionDigits: euros % 1 === 0 ? 0 : 2 })} €`
}

/**
 * Human label for a lead temperature.
 * @param temperature - Raw temperature value.
 * @returns Localized label.
 */
function temperatureLabel(temperature: string): string {
  return TEMPERATURE_LABELS[temperature] ?? temperature
}

/**
 * Tailwind classes for a temperature badge.
 * @param temperature - Raw temperature value.
 * @returns Class string.
 */
function temperatureClass(temperature: string): string {
  switch (temperature) {
    case 'hot':
      return 'border border-[var(--app-red)]/40 bg-[var(--app-red)]/10 text-[var(--app-red)]'
    case 'warm':
      return 'border border-[var(--app-accent)]/40 bg-[var(--app-accent)]/10 text-[var(--app-accent)]'
    default:
      return 'border border-[var(--app-accent-ink)]/40 bg-[var(--app-accent-ink)]/10 text-[var(--app-accent-ink)]'
  }
}

/**
 * Inline style for a lead score progress bar (color scales with score).
 * @param score - Lead score 0–100.
 * @returns Inline style object.
 */
function scoreBarStyle(score: number): Record<string, string> {
  const color: string = score >= 70 ? 'var(--app-red)' : score >= 40 ? 'var(--app-accent)' : 'var(--app-accent-ink)'
  return {
    width: `${Math.max(0, Math.min(100, score))}%`,
    backgroundColor: color,
    boxShadow: `0 0 6px ${hexAlpha(color, 0.5)}`,
  }
}

/**
 * Format an ISO timestamp to a short French date-time.
 * @param ts - ISO timestamp.
 * @returns Human-readable date-time.
 */
function formatDate(ts: string): string {
  return new Date(ts).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** Persistent drawer stack — hot leads open the prospect drawer in place. */
const drawerStack = useDrawerStackStore()

/**
 * Open a hot lead's prospect drawer right here (no navigation). Falls back
 * to the prospects page deep-link if the fetch fails.
 * @param prospectId - Target prospect id.
 */
async function openProspect(prospectId: number): Promise<void> {
  try {
    const prospect = await getProspect(prospectId)
    drawerStack.push({ kind: 'prospect', prospect })
  } catch {
    navigateTo(`/dashboard/my-prospects?open=${prospectId}`)
  }
}

/**
 * Load (or refresh) every dashboard data source.
 * @returns Resolves once all sources have settled.
 */
async function load(): Promise<void> {
  isLoading.value = true
  try {
    const [s, leads, act] = await Promise.all([
      getDashboardStats(),
      getHotLeads().catch((): { items: HotLead[] } => ({ items: [] })),
      getDashboardActivity(14).catch((): { days: ActivityPoint[] } => ({ days: [] })),
    ])
    stats.value = s
    hotLeads.value = leads.items
    activity.value = act.days
    lastUpdated.value = new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
  } catch {
    stats.value = null
  } finally {
    isLoading.value = false
  }
}

onMounted(async (): Promise<void> => {
  await load()
})
</script>
