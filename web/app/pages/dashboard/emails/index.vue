<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-3xl font-bold text-[var(--app-ink)]">Suivi des emails</h1>
        <p class="text-muted mt-2 text-sm">Historique et statut de chaque email de prospection envoyé</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          :disabled="isLoading || isSyncing"
          class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
          :title="'Synchronise les statuts depuis Resend (utile en local sans webhook)'"
          @click="syncStatus"
        >
          <UIcon
            :name="isSyncing ? 'i-lucide-loader-circle' : 'i-lucide-rotate-cw'"
            :class="['h-4 w-4', isSyncing && 'animate-spin']"
          />
          {{ isSyncing ? 'Sync…' : 'Sync Resend' }}
        </button>
        <button
          :disabled="isLoading"
          class="btn-secondary disabled:cursor-not-allowed disabled:opacity-50"
          @click="loadLogs"
        >
          <UIcon name="i-lucide-rotate-cw" class="h-4 w-4" />
          Actualiser
        </button>
        <button class="btn-primary" @click="drawerStack.push({ kind: 'send-email', prospect: null })">
          <UIcon name="i-lucide-send" class="h-4 w-4" />
          Envoyer un email
        </button>
      </div>
    </div>

    <!-- Stats cards -->
    <div class="grid grid-cols-2 gap-4 md:grid-cols-6">
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Envoyés</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ stats.total_sent }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Délivrés</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-green)]">{{ stats.total_delivered }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Ouverts</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-violet)]">{{ stats.total_opened }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Cliqués</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ stats.total_clicked }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Bounces</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-red)]">{{ stats.total_bounced }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Taux ouv.</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ stats.open_rate }}%</p>
      </div>
    </div>

    <!-- Filters -->
    <div class="card">
      <div class="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Rechercher</label>
          <input v-model="searchQuery" type="text" placeholder="Email, nom, sujet..." class="input-field" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Statut</label>
          <UiSelectField v-model="filterStatus" :options="statusOptions" />
        </div>
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Campagne</label>
          <UiSelectField v-model="filterCampaignId" :options="campaignOptions" />
        </div>
        <div class="flex items-end">
          <button class="btn-secondary w-full" @click="clearFilters">Réinitialiser</button>
        </div>
      </div>
    </div>

    <!-- Error -->
    <div
      v-if="error"
      class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]"
    >
      <p class="font-semibold">Erreur de chargement</p>
      <p class="text-muted mt-1 text-sm">{{ error }}</p>
    </div>

    <!-- Loader -->
    <div v-else-if="isLoading" class="flex items-center justify-center py-12">
      <UIcon name="i-lucide-loader-circle" class="text-muted h-9 w-9 animate-spin" />
    </div>

    <!-- Empty -->
    <div v-else-if="filteredLogs.length === 0" class="card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun email trouvé</h3>
      <p class="text-muted mt-2 text-sm">
        {{
          filterStatus !== 'all' || filterCampaignId !== 'all' || searchQuery
            ? 'Modifiez vos filtres'
            : 'Lancez une campagne pour commencer'
        }}
      </p>
    </div>

    <!-- Table -->
    <div v-else class="card overflow-hidden">
      <table class="w-full border-collapse">
        <thead>
          <tr class="bg-[var(--app-bg)]">
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Destinataire</th>
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Sujet</th>
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Campagne</th>
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Statut</th>
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Activité</th>
            <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Envoyé le</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="log in paginatedLogs"
            :key="log.id"
            class="border-muted cursor-pointer border-b transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]"
            @click="openDrawer(log)"
          >
            <td class="px-3 py-2.5">
              <div class="text-sm font-medium text-[var(--app-ink)]">
                {{ log.recipient_name || log.recipient_email }}
              </div>
              <div class="text-muted text-xs">{{ log.recipient_email }}</div>
            </td>
            <td class="text-muted max-w-[200px] truncate px-3 py-2.5 text-sm">
              {{ log.subject }}
            </td>
            <td class="text-muted px-3 py-2.5 text-sm">
              {{ resolveCampaignName(log.campaign_id) ?? '—' }}
            </td>
            <td class="px-3 py-2.5">
              <div class="flex flex-wrap gap-1">
                <UiEmailStatusBadge v-for="s in getEmailBadges(log)" :key="s" :status="s" />
              </div>
            </td>
            <td class="px-3 py-2.5">
              <div class="flex items-center gap-2">
                <span
                  v-for="step in getEngagement(log)"
                  :key="step.key"
                  :title="step.ts ? `${step.label} — ${formatDate(step.ts)}` : `${step.label} : pas encore`"
                  class="flex h-6 w-6 items-center justify-center rounded-md"
                  :class="step.ts ? 'bg-[var(--app-surface)]' : 'bg-transparent'"
                >
                  <UIcon
                    :name="step.icon"
                    class="h-3.5 w-3.5"
                    :class="step.ts ? step.color : 'text-[var(--app-faint)]'"
                  />
                </span>
              </div>
            </td>
            <td class="px-3 py-2.5 text-sm">
              <div class="text-[var(--app-ink)]">{{ log.sent_at ? formatDate(log.sent_at) : '—' }}</div>
              <div v-if="lastActivityAt(log) && lastActivityAt(log) !== log.sent_at" class="text-muted mt-0.5 text-xs">
                Activité : {{ formatDate(lastActivityAt(log)) }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div class="flex items-center justify-between border-t border-[var(--app-line)] px-6 py-4">
        <div class="text-muted text-sm">
          {{ (currentPage - 1) * pageSize + 1 }}–{{ Math.min(currentPage * pageSize, filteredLogs.length) }} sur
          {{ filteredLogs.length }}
        </div>
        <div class="flex items-center gap-2">
          <button
            :disabled="currentPage === 1"
            class="btn-secondary h-auto min-h-0 px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage--"
          >
            Précédent
          </button>
          <span class="text-muted text-sm">{{ currentPage }} / {{ totalPages }}</span>
          <button
            :disabled="currentPage === totalPages"
            class="btn-secondary h-auto min-h-0 px-3 py-1 text-xs disabled:cursor-not-allowed disabled:opacity-50"
            @click="currentPage++"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { EmailLog, EmailStats, EmailStatus } from '~/types'
import { formatDate } from '~/utils/date'
import { getEmailLogs, getEmailStats } from '~/services/emailCampaignsService'
import { campaignService, type CampaignResponse } from '~/services/campaignService'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { api } from '~/services/api'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

// ─── State ────────────────────────────────────────────────────────────────────

const toast = useToast()
const logs = ref<EmailLog[]>([])
const campaigns = ref<CampaignResponse[]>([])

// ─── Envoi manuel (drawer persistant hébergé par le layout) ──────────────────

/** Persistent drawer stack (composer + email log detail live there). */
const drawerStack = useDrawerStackStore()

const isSyncing = ref<boolean>(false)
const isLoading = ref(false)
const error = ref<string | null>(null)
const searchQuery = ref('')
const filterStatus = ref('all')
const filterCampaignId = ref('all')
const currentPage = ref(1)
const pageSize = 50

/** Full stats object — typed strictly as EmailStats so every field is present. */
const stats = ref<EmailStats>({
  total_sent: 0,
  total_delivered: 0,
  total_opened: 0,
  total_clicked: 0,
  total_bounced: 0,
  total_failed: 0,
  delivery_rate: 0,
  open_rate: 0,
  click_rate: 0,
})

// ─── Filter options ───────────────────────────────────────────────────────────

const statusOptions = [
  { value: 'all', label: 'Tous' },
  { value: 'pending', label: 'En attente' },
  { value: 'sent', label: 'Envoyé' },
  { value: 'delivered', label: 'Délivré' },
  { value: 'delivery_delayed', label: 'Retardé' },
  { value: 'opened', label: 'Ouvert' },
  { value: 'clicked', label: 'Cliqué' },
  { value: 'bounced', label: 'Bounced' },
  { value: 'failed', label: 'Échoué' },
  { value: 'complained', label: 'Spam' },
]

const campaignOptions = computed(() => [
  { value: 'all', label: 'Toutes les campagnes' },
  ...campaigns.value.map((c) => ({ value: String(c.id), label: c.name })),
])

// ─── Computed ─────────────────────────────────────────────────────────────────

const filteredLogs = computed((): EmailLog[] => {
  let list = logs.value

  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(
      (l) =>
        l.recipient_email.toLowerCase().includes(q) ||
        l.recipient_name?.toLowerCase().includes(q) ||
        l.subject.toLowerCase().includes(q),
    )
  }

  if (filterStatus.value !== 'all') {
    list = list.filter((l) => l.status === filterStatus.value)
  }

  if (filterCampaignId.value !== 'all') {
    // campaign_id on EmailLog is ``string | null`` from the backend; compare
    // against the filter value (also a string) to avoid Number(null) → 0 bugs.
    list = list.filter((l) => l.campaign_id != null && String(l.campaign_id) === filterCampaignId.value)
  }

  return list
})

const totalPages = computed((): number => Math.max(1, Math.ceil(filteredLogs.value.length / pageSize)))

const paginatedLogs = computed((): EmailLog[] => {
  const start = (currentPage.value - 1) * pageSize
  return filteredLogs.value.slice(start, start + pageSize)
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Resolve a campaign display name from its ID.
 * @param id - Campaign ID as stored on ``EmailLog.campaign_id`` (may be null).
 * @returns Campaign name, or ``undefined`` when the ID is missing or unknown.
 */
function resolveCampaignName(id: string | number | null | undefined): string | undefined {
  if (id == null) return undefined
  const numericId = Number(id)
  if (Number.isNaN(numericId)) return undefined
  return campaigns.value.find((c) => c.id === numericId)?.name
}

/**
 * Returns the list of status badges to display for a given email log.
 *
 * Shows the best positive state reached (based on event timestamps) plus any
 * negative events as additional badges (e.g. "Ouvert" + "Spam").
 * @param log - The email log entry to evaluate.
 * @returns Ordered array of EmailStatus values to render as badges.
 */
function getEmailBadges(log: EmailLog): EmailStatus[] {
  const badges: EmailStatus[] = []

  // Primary badge: highest positive event reached (timestamp-based)
  if (log.clicked_at) badges.push('clicked')
  else if (log.opened_at) badges.push('opened')
  else if (log.delivered_at) badges.push('delivered')
  else badges.push(log.status)

  // Complaint is shown as an additional badge alongside any positive state
  if (log.complained_at && !badges.includes('complained')) {
    badges.push('complained')
  }

  return badges
}

/** A single engagement signal (delivered / opened / clicked) for the table. */
interface EngagementStep {
  /** Stable key. */
  key: string
  /** French label shown in the tooltip. */
  label: string
  /** Lucide icon name. */
  icon: string
  /** Event timestamp, or null/undefined when it hasn't happened. */
  ts: string | null | undefined
  /** Tailwind text colour applied when the signal is reached. */
  color: string
}

/**
 * Build the engagement signals (delivered → opened → clicked) for a log row.
 *
 * These are the Resend-tracked events most useful at a glance for cold
 * outreach.  Each step lights up in colour once reached.
 * @param log - The email log entry to evaluate.
 * @returns Ordered list of engagement steps.
 */
function getEngagement(log: EmailLog): EngagementStep[] {
  return [
    {
      key: 'delivered',
      label: 'Délivré',
      icon: 'i-lucide-circle-check',
      ts: log.delivered_at,
      color: 'text-[var(--app-green)]',
    },
    {
      key: 'opened',
      label: 'Ouvert',
      icon: 'i-lucide-mail-open',
      ts: log.opened_at,
      color: 'text-[var(--app-violet)]',
    },
    {
      key: 'clicked',
      label: 'Cliqué',
      icon: 'i-lucide-mouse-pointer-click',
      ts: log.clicked_at,
      color: 'text-[var(--app-ink)]',
    },
  ]
}

/**
 * Returns the timestamp of the most recent tracked event for a log.
 * @param log - The email log entry to evaluate.
 * @returns The latest event ISO timestamp, or null when none is set.
 */
function lastActivityAt(log: EmailLog): string | null {
  const stamps: (string | null | undefined)[] = [
    log.sent_at,
    log.delivered_at,
    log.opened_at,
    log.clicked_at,
    log.bounced_at,
    log.complained_at,
    log.failed_at,
  ]
  const valid: number[] = stamps.filter((s): s is string => !!s).map((s: string): number => new Date(s).getTime())
  if (valid.length === 0) return null
  return new Date(Math.max(...valid)).toISOString()
}

function clearFilters(): void {
  searchQuery.value = ''
  filterStatus.value = 'all'
  filterCampaignId.value = 'all'
  currentPage.value = 1
}

function openDrawer(log: EmailLog): void {
  drawerStack.push({ kind: 'email-log', log, campaignName: resolveCampaignName(log.campaign_id) })
}

// ─── Data loading ─────────────────────────────────────────────────────────────

async function loadLogs(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    const [logsRes, campaignsRes, statsRes] = await Promise.all([
      getEmailLogs({ limit: 500 }),
      campaignService.list(0, 200),
      getEmailStats(),
    ])
    logs.value = logsRes.logs
    campaigns.value = campaignsRes.campaigns
    stats.value = statsRes
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des emails'
  } finally {
    isLoading.value = false
  }
}

// Un email envoyé depuis le drawer (d'ici ou d'une fiche prospect) rafraîchit la liste.
watch(
  (): number => drawerStack.emailLogsRefreshCounter,
  (): void => {
    void loadLogs()
  },
)

/**
 * Poll the Resend API for the latest status of all unresolved emails.
 * Useful in local development where the webhook is not publicly reachable.
 * @returns A promise that resolves once the sync is complete.
 */
async function syncStatus(): Promise<void> {
  isSyncing.value = true
  try {
    const result = await api.post<{ updated: number; checked: number; errors?: string[] }>(
      '/api/v1/emails/sync-resend-status',
      {},
    )
    if (result.updated > 0) {
      toast.success(`${result.updated} statut(s) mis à jour`)
      await loadLogs()
    } else if (result.checked === 0) {
      toast.warning(
        "Aucun email à synchroniser — vérifiez que le Message ID Resend est bien stocké (ouvrez le drawer d'un email)",
      )
    } else {
      toast.info(`${result.checked} email(s) vérifiés — aucun changement`)
    }
    if (result.errors && result.errors.length > 0) {
      console.error('[Sync Resend] Errors:', result.errors)
      toast.error(result.errors[0] ?? 'Erreur Resend — voir la console')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la synchronisation')
  } finally {
    isSyncing.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadLogs()
  // Auto-sync on page load so statuses are fresh even without webhooks
  await syncStatus()
})
</script>
