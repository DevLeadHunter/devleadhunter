<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-[#f9f9f9]">Tableau de bord</h1>
      <p class="text-muted mt-2 text-sm">Vue d'ensemble de votre tunnel, de la prospection à la vente</p>
    </div>

    <div v-if="isLoading" class="flex items-center justify-center py-16">
      <i class="fa-solid fa-spinner fa-spin text-muted text-4xl"></i>
    </div>

    <template v-else-if="stats">
      <!-- Pipeline KPIs -->
      <div class="grid grid-cols-1 gap-6 md:grid-cols-3">
        <NuxtLink to="/dashboard/my-prospects" class="card transition-colors hover:border-[#30363d]">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-muted text-sm font-medium">Prospects</p>
              <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ stats.prospects_total }}</p>
            </div>
            <i class="fa-solid fa-users text-2xl text-[#8b949e]"></i>
          </div>
        </NuxtLink>
        <NuxtLink to="/dashboard/demo-sites" class="card transition-colors hover:border-[#30363d]">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-muted text-sm font-medium">Démos actives</p>
              <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ stats.demo_sites_active }}</p>
            </div>
            <i class="fa-solid fa-globe text-2xl text-[#8b949e]"></i>
          </div>
        </NuxtLink>
        <NuxtLink to="/dashboard/campaigns" class="card transition-colors hover:border-[#30363d]">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-muted text-sm font-medium">Campagnes actives</p>
              <p class="mt-2 text-3xl font-bold text-[#f9f9f9]">{{ stats.campaigns_active }}</p>
            </div>
            <i class="fa-solid fa-bullhorn text-2xl text-[#8b949e]"></i>
          </div>
        </NuxtLink>
      </div>

      <!-- Hot leads -->
      <div v-if="hotLeads.length" class="card">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[#f9f9f9]">
            <i class="fa-solid fa-fire mr-1.5 text-[#ff7b72]"></i>Leads chauds
          </h2>
          <NuxtLink to="/dashboard/my-prospects" class="text-xs text-[#58a6ff] hover:underline">
            Tous les prospects →
          </NuxtLink>
        </div>
        <div class="space-y-2">
          <button
            v-for="lead in hotLeads"
            :key="lead.prospect_id"
            type="button"
            class="flex w-full items-center gap-3 rounded-lg border border-[#1f1f1f] p-3 text-left transition-colors hover:border-[#30363d] hover:bg-[#1a1a1a]"
            @click="openProspect(lead.prospect_id)"
          >
            <span
              :class="[
                'inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium',
                temperatureClass(lead.temperature),
              ]"
            >
              {{ temperatureLabel(lead.temperature) }}
            </span>
            <div class="min-w-0 flex-1">
              <p class="truncate text-sm font-medium text-[#f9f9f9]">{{ lead.name }}</p>
              <p class="text-xs text-[#8b949e]">
                {{ lead.city || '—' }}<span v-if="lead.last_seen"> · {{ formatDate(lead.last_seen) }}</span>
              </p>
            </div>
            <span class="text-sm font-bold text-[#f9f9f9]"
              >{{ lead.score }}<span class="text-xs text-[#8b949e]">/100</span></span
            >
            <i class="fa-solid fa-chevron-right text-xs text-[#8b949e]"></i>
          </button>
        </div>
      </div>

      <!-- Email engagement -->
      <div class="card">
        <h2 class="mb-4 text-sm font-semibold text-[#f9f9f9]">Engagement email</h2>
        <div class="grid grid-cols-2 gap-6 md:grid-cols-5">
          <div>
            <p class="text-muted text-xs">Envoyés</p>
            <p class="mt-1 text-2xl font-bold text-[#f9f9f9]">{{ stats.emails_sent }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Ouverts</p>
            <p class="mt-1 text-2xl font-bold text-[#f9f9f9]">{{ stats.emails_opened }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Cliqués</p>
            <p class="mt-1 text-2xl font-bold text-[#f9f9f9]">{{ stats.emails_clicked }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Taux d'ouverture</p>
            <p class="mt-1 text-2xl font-bold text-[#58a6ff]">{{ stats.open_rate }}%</p>
          </div>
          <div>
            <p class="text-muted text-xs">Taux de clic</p>
            <p class="mt-1 text-2xl font-bold text-[#58a6ff]">{{ stats.click_rate }}%</p>
          </div>
        </div>
      </div>

      <!-- Sales -->
      <div class="card">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[#f9f9f9]">Ventes</h2>
          <NuxtLink to="/dashboard/orders" class="text-xs text-[#58a6ff] hover:underline">Voir les ventes →</NuxtLink>
        </div>
        <div class="grid grid-cols-2 gap-6 md:grid-cols-4">
          <div>
            <p class="text-muted text-xs">Chiffre d'affaires</p>
            <p class="mt-1 text-2xl font-bold text-[#3fb950]">{{ formatCents(stats.revenue_cents) }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Ventes gagnées</p>
            <p class="mt-1 text-2xl font-bold text-[#f9f9f9]">{{ stats.sales_won }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Commandes</p>
            <p class="mt-1 text-2xl font-bold text-[#f9f9f9]">{{ stats.orders_total }}</p>
          </div>
          <div>
            <p class="text-muted text-xs">Pipeline</p>
            <p class="mt-1 text-2xl font-bold text-[#e3b341]">{{ formatCents(stats.pipeline_cents) }}</p>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="rounded-lg border border-[#DC4747] bg-[#1a1a1a] p-4 text-[#DC4747]">
      <p class="text-sm">Impossible de charger les statistiques.</p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import type { Ref } from 'vue'
import type { DashboardStats, HotLead } from '~/services/dashboardService'
import { getDashboardStats, getHotLeads } from '~/services/dashboardService'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const stats: Ref<DashboardStats | null> = ref<DashboardStats | null>(null)
const hotLeads: Ref<HotLead[]> = ref<HotLead[]>([])
const isLoading: Ref<boolean> = ref(false)

const TEMPERATURE_LABELS: Record<string, string> = {
  hot: 'Chaud',
  warm: 'Tiède',
  cold: 'Froid',
  unknown: 'Inconnu',
}

/**
 * Format an amount in cents as euros.
 * @param cents - Amount in cents.
 * @returns Formatted euro string.
 */
function formatCents(cents: number): string {
  const euros = cents / 100
  return `${euros % 1 === 0 ? euros.toFixed(0) : euros.toFixed(2)} €`
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
      return 'border border-[#da3633]/40 bg-[#da3633]/10 text-[#ff7b72]'
    case 'warm':
      return 'border border-[#e3b341]/40 bg-[#e3b341]/10 text-[#e3b341]'
    default:
      return 'border border-[#58a6ff]/40 bg-[#58a6ff]/10 text-[#58a6ff]'
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

/**
 * Open a prospect's drawer on the prospects page.
 * @param prospectId - Target prospect id.
 */
function openProspect(prospectId: number): void {
  navigateTo(`/dashboard/my-prospects?open=${prospectId}`)
}

onMounted(async (): Promise<void> => {
  isLoading.value = true
  try {
    const [s, leads] = await Promise.all([
      getDashboardStats(),
      getHotLeads().catch((): { items: HotLead[] } => ({ items: [] })),
    ])
    stats.value = s
    hotLeads.value = leads.items
  } catch {
    stats.value = null
  } finally {
    isLoading.value = false
  }
})
</script>
