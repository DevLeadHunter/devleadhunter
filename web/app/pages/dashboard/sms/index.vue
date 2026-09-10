<template>
  <div class="space-y-6">
    <div class="flex flex-col gap-4 @2xl:flex-row @2xl:items-end @2xl:justify-between">
      <div class="min-w-0">
        <p class="app-label flex items-center gap-2">
          <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
          Prospection
        </p>
        <h1 class="app-page-title mt-2">Suivi des SMS</h1>
        <p class="mt-1.5 text-sm text-[var(--app-ink-soft)]">
          Historique et statut de chaque SMS envoyé à vos prospects
        </p>
      </div>
      <div
        class="flex w-full flex-col-reverse items-stretch gap-2 sm:flex-row sm:flex-wrap sm:items-center sm:justify-end @2xl:w-auto"
      >
        <div class="flex flex-wrap items-center gap-2 sm:gap-3">
          <NuxtLink to="/dashboard/settings/sms" class="app-btn-secondary h-9 shrink-0 px-4 text-xs whitespace-nowrap">
            <UIcon name="i-lucide-settings-2" class="h-3.5 w-3.5" />
            Relance & expéditeur
          </NuxtLink>
          <button
            :disabled="isLoading"
            class="app-btn-secondary h-9 shrink-0 px-4 text-xs whitespace-nowrap disabled:cursor-not-allowed disabled:opacity-50"
            @click="loadAll"
          >
            <UIcon name="i-lucide-rotate-cw" :class="['h-3.5 w-3.5', isLoading && 'animate-spin']" />
            Actualiser
          </button>
        </div>
        <button
          class="app-btn-primary h-9 w-full shrink-0 px-4 text-xs sm:w-auto"
          @click="drawerStack.push({ kind: 'send-sms', prospect: null })"
        >
          <UIcon name="i-lucide-send" class="h-3.5 w-3.5" />
          Envoyer un SMS
        </button>
      </div>
    </div>

    <div :class="['grid grid-cols-2 gap-3', canSeeCredit ? '@sm:grid-cols-5' : '@sm:grid-cols-4']">
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Envoyés</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ stats.sent }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Délivrés</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-green)]">{{ stats.delivered }}</p>
      </div>
      <div class="card text-center">
        <p class="text-muted text-xs font-medium">Échecs</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-red)]">{{ stats.failed }}</p>
      </div>
      <div class="card text-center" title="Estimation : segments facturés × tarif smsmode par segment">
        <p class="text-muted text-xs font-medium">Coût estimé</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ formatEuros(stats.cost_cents) }}</p>
      </div>
      <div
        v-if="canSeeCredit"
        class="card text-center"
        title="Solde de crédits restant sur le compte smsmode (compte plateforme partagé)"
      >
        <p class="text-muted text-xs font-medium">Crédits restants</p>
        <p class="mt-1 text-2xl font-bold text-[var(--app-ink)]">{{ creditLabel }}</p>
      </div>
    </div>

    <div
      v-if="error"
      class="rounded-lg border border-[var(--app-red)] bg-[var(--app-surface)] p-4 text-[var(--app-red)]"
    >
      <p class="font-semibold">Erreur de chargement</p>
      <p class="text-muted mt-1 text-sm">{{ error }}</p>
    </div>

    <div v-else-if="isLoading" class="flex items-center justify-center py-12">
      <UIcon name="i-lucide-loader-circle" class="text-muted h-9 w-9 animate-spin" />
    </div>

    <div v-else-if="messages.length === 0" class="card px-6 py-12 text-center">
      <LandingAsterisk class="text-4xl text-[var(--app-accent)]" />
      <h3 class="font-display mt-5 text-2xl font-semibold text-[var(--app-ink)]">Aucun SMS envoyé</h3>
      <p class="text-muted mt-2 text-sm">
        Envoyez un SMS manuel, ou relancez vos prospects sans réponse depuis les réglages.
      </p>
      <button class="app-btn-primary mx-auto mt-5" @click="drawerStack.push({ kind: 'send-sms', prospect: null })">
        <UIcon name="i-lucide-send" class="h-3.5 w-3.5" />
        Envoyer un SMS
      </button>
    </div>

    <div v-else class="card overflow-hidden">
      <div class="md:overflow-x-auto">
        <table class="dlh-card-table w-full min-w-[640px] border-collapse">
          <thead>
            <tr class="bg-[var(--app-bg)]">
              <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Destinataire</th>
              <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Message</th>
              <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Statut</th>
              <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">SMS</th>
              <th class="text-muted border-muted border-b px-3 py-2.5 text-left text-xs font-semibold">Envoyé le</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="message in messages"
              :key="message.id"
              class="border-muted cursor-pointer border-b transition-colors last:border-b-0 hover:bg-[var(--app-surface-2)]"
              @click="openDrawer(message)"
            >
              <td class="px-3 py-2.5">
                <div class="text-sm font-medium text-[var(--app-ink)]">
                  {{ message.recipient_name || message.to_e164 }}
                </div>
                <div class="text-muted text-xs">{{ message.to_e164 }}</div>
              </td>
              <td data-label="Message" class="text-muted max-w-[260px] truncate px-3 py-2.5 text-sm">
                {{ message.body }}
              </td>
              <td data-label="Statut" class="px-3 py-2.5">
                <span :class="['app-badge', SMS_STATUS_BADGE_CLASS[message.status] ?? '']">
                  {{ SMS_STATUS_LABELS[message.status] ?? message.status }}
                </span>
                <p
                  v-if="message.status === 'failed' && (message.status_detail || message.error)"
                  class="mt-1 text-[11px] text-[var(--app-red)]"
                >
                  {{ message.status_detail ? smsStatusDetailLabel(message.status_detail) : message.error }}
                </p>
              </td>
              <td data-label="SMS" class="text-muted px-3 py-2.5 text-sm tabular-nums">
                {{ message.segments }}
              </td>
              <td data-label="Envoyé le" class="px-3 py-2.5 text-sm text-[var(--app-ink)]">
                {{ formatCompactDateTime(message.created_at) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, ref, watch } from 'vue'
import type { SmsCredit, SmsMessage, SmsMessagesResponse, SmsStats } from '~/services/smsService'
import { SmsService } from '~/services/smsService'
import { SMS_STATUS_BADGE_CLASS, SMS_STATUS_LABELS, smsStatusDetailLabel } from '~/constants/smsStatus'
import { formatEuros } from '~/utils/currency'
import { formatCompactDateTime } from '~/utils/date'
import { isPlatformAdmin } from '~/utils/userRoles'
import { useDrawerStackStore } from '~/stores/drawerStack'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

/** Persistent drawer stack (the SMS composer lives there). */
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()
/** Current user — the smsmode balance is an account-level fact, admins only. */
const userStore: ReturnType<typeof useUserStore> = useUserStore()

const messages: Ref<SmsMessage[]> = ref([])
const isLoading: Ref<boolean> = ref(false)
const error: Ref<string | null> = ref(null)

const stats: Ref<SmsStats> = ref({
  total: 0,
  sent: 0,
  delivered: 0,
  failed: 0,
  pending: 0,
  cost_cents: 0,
})

/** The platform smsmode balance, once fetched (admin-only, null when unreadable). */
const credit: Ref<SmsCredit | null> = ref(null)

/** Whether the current user may see the shared smsmode credit balance. */
const canSeeCredit: ComputedRef<boolean> = computed((): boolean => isPlatformAdmin(userStore.user?.role))

/** The credit card value in euros (same format as « Coût estimé »), or « — » while unknown. */
const creditLabel: ComputedRef<string> = computed((): string => {
  const value: number | null | undefined = credit.value?.credits
  return formatEuros(typeof value === 'number' ? Math.round(value * 100) : null)
})

/**
 * Open the SMS detail drawer for a row.
 * @param message - The SMS to display.
 */
function openDrawer(message: SmsMessage): void {
  drawerStack.push({ kind: 'sms-log', message })
}

/**
 * Fetch the shared smsmode credit balance (admins only).
 * Non-fatal: a failed read leaves the card on « — » and never blocks the page.
 */
async function loadCredit(): Promise<void> {
  if (!canSeeCredit.value) return
  try {
    credit.value = await SmsService.getCredit()
  } catch {
    credit.value = null
  }
}

/** Fetch the SMS history and stats. */
async function loadAll(): Promise<void> {
  isLoading.value = true
  error.value = null
  try {
    const [list, statsRes]: [SmsMessagesResponse, SmsStats] = await Promise.all([
      SmsService.listMessages(500),
      SmsService.getStats(),
    ])
    messages.value = list.messages
    stats.value = statsRes
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : 'Erreur lors du chargement des SMS'
  } finally {
    isLoading.value = false
  }
  void loadCredit()
}

// A SMS sent from the composer refreshes the list.
watch(
  (): number => drawerStack.smsMessagesRefreshCounter,
  (): void => {
    void loadAll()
  },
)

onMounted(async (): Promise<void> => {
  await loadAll()
})
</script>
