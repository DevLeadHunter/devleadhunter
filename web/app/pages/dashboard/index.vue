<template>
  <div class="space-y-8">
    <div class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Pilotage
        </p>
        <h1 class="app-page-title mt-2">Tableau de bord</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          Votre activité en un coup d'œil, de la prospection à la vente.
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <div class="flex overflow-hidden rounded-lg border border-[var(--app-line)]">
          <button
            v-for="preset in PERIOD_PRESETS"
            :key="preset.days"
            type="button"
            class="cursor-pointer px-2.5 py-1.5 text-xs font-medium whitespace-nowrap transition-colors"
            :class="
              periodDays === preset.days
                ? 'bg-[var(--app-ink)] text-[var(--app-surface)]'
                : 'bg-[var(--app-surface)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
            "
            @click="changePeriod(preset.days)"
          >
            {{ preset.label }}
          </button>
        </div>
        <button type="button" class="app-btn-secondary h-8 px-3 text-xs" :disabled="isLoading" @click="load">
          <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
          Actualiser
        </button>
        <span v-if="lastUpdated" class="w-full text-xs text-[var(--app-ink-soft)] sm:w-auto">
          Mis à jour à {{ lastUpdated }}
        </span>
      </div>
    </div>

    <div v-if="isLoading && !stats" class="space-y-8">
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div v-for="n in 4" :key="n" class="app-card h-28 animate-pulse"></div>
      </div>
      <div class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="app-card h-72 animate-pulse lg:col-span-2"></div>
        <div class="app-card h-72 animate-pulse"></div>
      </div>
    </div>

    <template v-else-if="stats">
      <section>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <NuxtLink
            v-for="stage in pipelineTiles"
            :key="stage.label"
            :to="stage.to"
            class="app-card group relative flex flex-col gap-1.5 p-4 transition-all hover:-translate-y-0.5"
          >
            <div class="flex items-center justify-between">
              <p class="app-label">{{ stage.label }}</p>
              <UIcon :name="stage.icon" class="h-4 w-4 text-[var(--app-faint)]" />
            </div>
            <p class="text-2xl font-bold text-[var(--app-ink)] tabular-nums">{{ stage.value }}</p>
            <p class="text-[11px] leading-snug text-[var(--app-ink-soft)]">{{ stage.hint }}</p>
            <span
              class="mt-1 inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink)] opacity-0 transition-opacity group-hover:opacity-100"
            >
              {{ stage.linkLabel }} <UIcon name="i-lucide-arrow-right" class="h-3 w-3" />
            </span>
          </NuxtLink>
        </div>
      </section>

      <section class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div class="app-card p-5 md:p-6 lg:col-span-2">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="flex items-center gap-2 text-sm font-semibold text-[var(--app-ink)]">
              <UIcon name="i-lucide-flame" class="h-4 w-4 text-[var(--app-red)]" />
              Leads chauds
              <span v-if="hotLeads.length" class="font-normal text-[var(--app-ink-soft)]">
                ({{ hotLeads.length }})
              </span>
            </h2>
            <NuxtLink to="/dashboard/my-prospects" class="text-xs font-medium text-[var(--app-ink)] hover:underline">
              Tous les prospects →
            </NuxtLink>
          </div>

          <div v-if="displayedHotLeads.length" class="divide-y divide-[var(--app-line-soft)]">
            <button
              v-for="lead in displayedHotLeads"
              :key="lead.prospect_id"
              type="button"
              class="group flex w-full cursor-pointer items-center gap-3 py-2.5 text-left transition-colors first:pt-0 last:pb-0"
              @click="openProspect(lead.prospect_id)"
            >
              <span
                class="inline-flex w-14 shrink-0 items-center justify-center rounded-full px-2 py-0.5 text-[10px] font-semibold"
                :style="temperatureStyle(lead.temperature)"
              >
                {{ temperatureLabel(lead.temperature) }}
              </span>
              <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium text-[var(--app-ink)] group-hover:underline">
                  {{ lead.name }}
                </p>
                <p class="truncate text-[11px] text-[var(--app-ink-soft)]">
                  {{ lead.city || '—' }}<span v-if="lead.last_seen"> · vu {{ formatDate(lead.last_seen) }}</span>
                </p>
              </div>
              <div class="flex shrink-0 items-center gap-2.5">
                <div class="hidden h-1.5 w-16 overflow-hidden rounded-full bg-[var(--app-surface-2)] lg:block">
                  <div
                    class="h-full rounded-full bg-[var(--app-ink)]"
                    :style="{ width: `${Math.min(lead.score, 100)}%` }"
                  ></div>
                </div>
                <span class="w-8 text-right text-sm font-bold text-[var(--app-ink)] tabular-nums">
                  {{ lead.score }}
                </span>
                <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5 text-[var(--app-ink-soft)]" />
              </div>
            </button>
          </div>

          <div v-else class="flex flex-col items-center gap-2 py-10 text-center">
            <UIcon name="i-lucide-snowflake" class="h-7 w-7 text-[var(--app-faint)]" />
            <p class="text-sm text-[var(--app-ink-soft)]">Aucun lead chaud pour l'instant.</p>
            <p class="max-w-xs text-xs text-[var(--app-ink-soft)]">
              Les prospects qui ouvrent vos emails et visitent leur démo apparaîtront ici.
            </p>
          </div>
        </div>

        <div class="app-card p-4 md:p-5">
          <h2 class="mb-3 text-sm font-semibold text-[var(--app-ink)]">Actions rapides</h2>
          <div class="space-y-2">
            <button
              type="button"
              class="group flex w-full cursor-pointer items-center gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-left transition-all hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)]"
              @click="openSearchDrawer"
            >
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
              >
                <UIcon name="i-lucide-search" class="h-4 w-4 text-[var(--app-ink)]" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-medium text-[var(--app-ink)]">Trouver des prospects</span>
                <span class="block truncate text-[11px] text-[var(--app-ink-soft)]">Métier + ville → artisans</span>
              </span>
              <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
            </button>

            <NuxtLink
              v-for="shortcut in QUICK_LINKS"
              :key="shortcut.to"
              :to="shortcut.to"
              class="group flex w-full items-center gap-3 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 transition-all hover:-translate-y-0.5 hover:border-[var(--app-ink-soft)]"
            >
              <span
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)]"
              >
                <UIcon :name="shortcut.icon" class="h-4 w-4 text-[var(--app-ink)]" />
              </span>
              <span class="min-w-0 flex-1">
                <span class="block text-sm font-medium text-[var(--app-ink)]">{{ shortcut.label }}</span>
                <span class="block truncate text-[11px] text-[var(--app-ink-soft)]">{{ shortcut.hint }}</span>
              </span>
              <UIcon name="i-lucide-chevron-right" class="h-3.5 w-3.5 shrink-0 text-[var(--app-ink-soft)]" />
            </NuxtLink>
          </div>
        </div>
      </section>

      <section class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <div class="app-card p-5 md:p-6">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Activité email — 30 jours</h2>
            <NuxtLink to="/dashboard/email-health" class="text-xs font-medium text-[var(--app-ink)] hover:underline">
              Santé email →
            </NuxtLink>
          </div>
          <EmailHealthVolumeChart
            v-if="trendDays.length"
            :labels="trendLabels"
            :sent="sentValues"
            :delivered="deliveredValues"
            :opened="openedValues"
          />
          <p v-else class="py-10 text-center text-sm text-[var(--app-ink-soft)]">
            Aucune activité email sur la période.
          </p>
          <div class="mt-4 flex items-center gap-6 border-t border-[var(--app-line-soft)] pt-3">
            <p class="text-xs text-[var(--app-ink-soft)]">
              Taux d'ouverture
              <span class="ml-1 font-semibold text-[var(--app-ink)] tabular-nums">{{ stats.open_rate }}%</span>
            </p>
            <p class="text-xs text-[var(--app-ink-soft)]">
              Taux de clic
              <span class="ml-1 font-semibold text-[var(--app-ink)] tabular-nums">{{ stats.click_rate }}%</span>
            </p>
          </div>
        </div>

        <div class="app-card p-5 md:p-6">
          <div class="mb-4 flex items-center justify-between">
            <h2 class="text-sm font-semibold text-[var(--app-ink)]">Tunnel de conversion</h2>
            <span v-if="funnelConversionLabel" class="text-xs text-[var(--app-ink-soft)] tabular-nums">
              {{ funnelConversionLabel }}
            </span>
          </div>
          <div class="space-y-3">
            <div v-for="(stage, index) in funnelStages" :key="stage.label">
              <div class="mb-1 flex items-baseline justify-between text-xs">
                <span class="font-medium text-[var(--app-ink)]">{{ stage.label }}</span>
                <span class="text-[var(--app-ink-soft)] tabular-nums">
                  {{ formatInt(stage.value) }}
                  <span v-if="index > 0" class="ml-1 text-[var(--app-faint)]">({{ stage.stepRate }}%)</span>
                </span>
              </div>
              <div class="h-2.5 overflow-hidden rounded-full bg-[var(--app-surface-2)]">
                <div
                  class="h-full rounded-full transition-all duration-700"
                  :style="{ width: `${stage.widthPct}%`, backgroundColor: stage.color }"
                ></div>
              </div>
            </div>
          </div>
          <div
            class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--app-line-soft)] pt-3"
          >
            <p class="text-xs text-[var(--app-ink-soft)]">
              Encaissé
              <span class="ml-1 text-sm font-bold text-[var(--app-green)] tabular-nums">
                {{ formatCents(stats.revenue_cents) }}
              </span>
            </p>
            <p class="text-xs text-[var(--app-ink-soft)]">
              Pipeline en cours
              <span class="ml-1 text-sm font-bold text-[var(--app-ink)] tabular-nums">
                {{ formatCents(stats.pipeline_cents) }}
              </span>
            </p>
            <NuxtLink to="/dashboard/orders" class="text-xs font-medium text-[var(--app-ink)] hover:underline">
              Voir les ventes →
            </NuxtLink>
          </div>
        </div>
      </section>
    </template>

    <div v-else class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]">
      <p class="text-sm">Impossible de charger les statistiques.</p>
      <button type="button" class="app-btn-secondary mt-3 h-9 px-3 text-xs" @click="load">Réessayer</button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { FunnelBarStage, PipelineTile } from '~/types/DashboardHomePage'
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref } from 'vue'
import type { DashboardStats, HotLead } from '~/services/dashboardService'
import { DashboardService } from '~/services/dashboardService'
import type { EmailHealthTrendDay } from '~/services/emailHealthService'
import { EmailHealthService } from '~/services/emailHealthService'
import { ProspectsService } from '~/services/prospectsService'
import { useDrawerStackStore } from '~/stores/drawerStack'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

/** Shortcuts of the quick-actions card (the search one opens a drawer instead). */
const QUICK_LINKS: { to: string; label: string; hint: string; icon: string }[] = [
  {
    to: '/dashboard/campaigns',
    label: 'Lancer une campagne',
    hint: 'Cold email A/B + relances',
    icon: 'i-lucide-megaphone',
  },
  { to: '/dashboard/coverage', label: 'Carte de prospection', hint: 'Où prospecter ensuite', icon: 'i-lucide-map' },
  {
    to: '/dashboard/email-health',
    label: 'Santé email',
    hint: 'Délivrabilité + réputation',
    icon: 'i-lucide-heart-pulse',
  },
]

/** Period presets for the KPI filter (0 = all time, the default). */
const PERIOD_PRESETS: { days: number; label: string }[] = [
  { days: 0, label: 'Depuis toujours' },
  { days: 7, label: '7 j' },
  { days: 30, label: '30 j' },
  { days: 90, label: '3 mois' },
]

const drawerStack = useDrawerStackStore()

const periodDays: Ref<number> = ref(0)
const stats: Ref<DashboardStats | null> = ref(null)
const hotLeads: Ref<HotLead[]> = ref([])
const trendDays: Ref<EmailHealthTrendDay[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const lastUpdated: Ref<string | null> = ref(null)

/** Hot leads limited to the most relevant ones (the page stays breathable). */
const displayedHotLeads: ComputedRef<HotLead[]> = computed((): HotLead[] => hotLeads.value.slice(0, 6))

/** The four linked stages of the pipeline strip. */
const pipelineTiles: ComputedRef<PipelineTile[]> = computed((): PipelineTile[] => {
  const s: DashboardStats | null = stats.value
  if (!s) return []
  return [
    {
      label: 'Prospects',
      value: formatInt(s.prospects_total),
      hint: `${formatInt(s.demo_sites_active)} avec démo active`,
      icon: 'i-lucide-users',
      to: '/dashboard/my-prospects',
      linkLabel: 'Mes prospects',
    },
    {
      label: 'Démos actives',
      value: formatInt(s.demo_sites_active),
      hint: 'En ligne sur demo.dibodev.fr',
      icon: 'i-lucide-app-window',
      to: '/dashboard/demo-sites',
      linkLabel: 'Sites démo',
    },
    {
      label: 'Emails envoyés',
      value: formatInt(s.emails_sent),
      hint: `${formatInt(s.campaigns_active)} campagne${s.campaigns_active > 1 ? 's' : ''} active${s.campaigns_active > 1 ? 's' : ''}`,
      icon: 'i-lucide-send',
      to: '/dashboard/campaigns',
      linkLabel: 'Campagnes',
    },
    {
      label: "Chiffre d'affaires",
      value: formatCents(s.revenue_cents),
      hint: `${formatInt(s.sales_won)} vente${s.sales_won > 1 ? 's' : ''} · pipeline ${formatCents(s.pipeline_cents)}`,
      icon: 'i-lucide-banknote',
      to: '/dashboard/orders',
      linkLabel: 'Ventes',
    },
  ]
})

/** ISO dates of the email activity series. */
const trendLabels: ComputedRef<string[]> = computed((): string[] =>
  trendDays.value.map((day: EmailHealthTrendDay): string => day.date),
)
/** Daily "sent" counts. */
const sentValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.sent),
)
/** Daily "delivered" counts. */
const deliveredValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.delivered),
)
/** Daily "opened" counts. */
const openedValues: ComputedRef<number[]> = computed((): number[] =>
  trendDays.value.map((day: EmailHealthTrendDay): number => day.opened),
)

/** Compact funnel bars: prospect → envoyé → ouvert → cliqué → vendu. */
const funnelStages: ComputedRef<FunnelBarStage[]> = computed((): FunnelBarStage[] => {
  const s: DashboardStats | null = stats.value
  if (!s) return []
  const raw: { label: string; value: number; color: string }[] = [
    { label: 'Prospects', value: s.prospects_total, color: 'var(--app-ink)' },
    { label: 'Emails envoyés', value: s.emails_sent, color: 'var(--app-ink)' },
    { label: 'Emails ouverts', value: s.emails_opened, color: 'var(--app-blue)' },
    { label: 'Emails cliqués', value: s.emails_clicked, color: 'var(--app-accent)' },
    { label: 'Ventes', value: s.sales_won, color: 'var(--app-green)' },
  ]
  const max: number = Math.max(...raw.map((stage): number => stage.value), 1)
  return raw.map((stage, index): FunnelBarStage => {
    const previous: number = index > 0 ? (raw[index - 1]?.value ?? 0) : 0
    return {
      ...stage,
      widthPct: Math.max((stage.value / max) * 100, stage.value > 0 ? 2 : 0),
      stepRate: previous > 0 ? Math.round((stage.value / previous) * 100) : 0,
    }
  })
})

/** Overall prospect → sale conversion label. */
const funnelConversionLabel: ComputedRef<string> = computed((): string => {
  const s: DashboardStats | null = stats.value
  if (!s || s.prospects_total <= 0) return ''
  const pct: number = Math.round((s.sales_won / s.prospects_total) * 1000) / 10
  return `${pct.toLocaleString('fr-FR')}% prospect → vente`
})

/**
 * Badge colors for a lead temperature (semantic status colors).
 * @param temperature - Raw temperature value.
 * @returns Inline style with soft background + colored text.
 */
function temperatureStyle(temperature: string): Record<string, string> {
  if (temperature === 'hot') return { color: 'var(--app-red)', backgroundColor: 'var(--app-red-soft)' }
  if (temperature === 'warm') return { color: 'var(--app-accent-ink)', backgroundColor: 'var(--app-accent-soft)' }
  return { color: 'var(--app-blue)', backgroundColor: 'var(--app-blue-soft)' }
}

/**
 * Human label for a lead temperature.
 * @param temperature - Raw temperature value.
 * @returns Localized label.
 */
function temperatureLabel(temperature: string): string {
  const labels: Record<string, string> = { hot: 'Chaud', warm: 'Tiède', cold: 'Froid', unknown: 'Inconnu' }
  return labels[temperature] ?? temperature
}

/**
 * Format an integer with French thousands separators.
 * @param value - Number to format.
 * @returns Locale-formatted string.
 */
function formatInt(value: number): string {
  return value.toLocaleString('fr-FR')
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
 * Format an ISO timestamp to a short French date-time.
 * @param iso - ISO timestamp.
 * @returns Human-readable date-time.
 */
function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('fr-FR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
}

/** Open the prospect-search drawer (same entry point as the search page). */
function openSearchDrawer(): void {
  drawerStack.push({ kind: 'search-prospects' })
}

/**
 * Switch the KPI period filter and reload the stats.
 * @param days - Rolling window in days (0 = all time).
 * @returns A promise resolved once reloaded.
 */
async function changePeriod(days: number): Promise<void> {
  if (periodDays.value === days) return
  periodDays.value = days
  await load()
}

/**
 * Open a hot lead's prospect drawer right here (no navigation). Falls back
 * to the prospects page deep-link if the fetch fails.
 * @param prospectId - Target prospect id.
 */
async function openProspect(prospectId: number): Promise<void> {
  try {
    const prospect = await ProspectsService.getProspect(prospectId)
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
    const [statsData, leads, trends] = await Promise.all([
      DashboardService.getDashboardStats(periodDays.value),
      DashboardService.getHotLeads().catch((): { items: HotLead[] } => ({ items: [] })),
      EmailHealthService.getEmailHealthTrends(30).catch((): { days: EmailHealthTrendDay[] } => ({ days: [] })),
    ])
    stats.value = statsData
    hotLeads.value = leads.items
    trendDays.value = trends.days
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
