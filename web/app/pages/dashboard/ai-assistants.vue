<template>
  <div class="flex min-h-full flex-col gap-6">
    <div>
      <p class="app-label flex items-center gap-2">
        <LandingAsterisk class="text-[0.6rem] text-[var(--app-accent)]" />
        Module IA
      </p>
      <h1 class="app-page-title mt-2">Assistants IA</h1>
      <p class="text-muted mt-1 max-w-2xl text-sm leading-relaxed">
        Les réceptionnistes IA générés pour vos prospects : lien de démo à envoyer, script à coller sur leur site, et
        les demandes captées 24h/24.
      </p>
    </div>

    <UiLoader v-if="isLoading" label="Chargement des assistants…" />

    <UiEmptyState
      v-else-if="hasLoadFailed"
      title="Chargement impossible"
      description="Les assistants et leurs demandes n'ont pas pu être chargés. Vérifiez votre connexion et réessayez."
    >
      <template #action>
        <button type="button" class="btn-secondary h-9 text-xs" @click="loadData()">
          <UIcon name="i-lucide-refresh-cw" class="mr-1.5 h-4 w-4" />
          Réessayer
        </button>
      </template>
    </UiEmptyState>

    <template v-else>
      <div class="grid grid-cols-1 gap-4 @sm:grid-cols-3">
        <UiStatCard label="Assistants actifs" :value="activeAssistantCount" icon="i-lucide-bot" accent="neutral" />
        <UiStatCard label="Demandes à traiter" :value="pendingRequestCount" icon="i-lucide-inbox" accent="neutral" />
        <UiStatCard label="Dernière demande" :value="latestRequestLabel" icon="i-lucide-clock" accent="neutral" />
      </div>

      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Mes assistants</h2>
          <span class="text-muted text-xs tabular-nums">{{ assistants.length }}</span>
        </div>

        <UiEmptyState
          v-if="assistants.length === 0"
          title="Aucun assistant généré"
          description="Ouvrez un prospect et cliquez « Générer un assistant IA » pour créer sa démo."
        >
          <template #action>
            <NuxtLink to="/dashboard/my-prospects" class="btn-secondary h-9 text-xs">
              <UIcon name="i-lucide-users" class="mr-1.5 h-4 w-4" />
              Voir mes prospects
            </NuxtLink>
          </template>
        </UiEmptyState>

        <div v-else class="grid gap-3 @2xl:grid-cols-2">
          <article v-for="assistant in assistants" :key="assistant.id" class="app-card flex min-w-0 flex-col gap-3 p-4">
            <div class="flex flex-wrap items-start justify-between gap-x-3 gap-y-1.5">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ assistant.business_name }}</p>
                <p class="text-muted truncate text-xs">
                  {{ assistant.assistant_name
                  }}<span v-if="demoLifetimeLabel(assistant)"> · {{ demoLifetimeLabel(assistant) }}</span>
                </p>
              </div>
              <div class="flex shrink-0 items-center gap-1.5">
                <span
                  v-if="assistant.churn_risk"
                  class="app-badge app-badge--strong"
                  title="Abonné depuis plus de 30 jours, aucune conversation ni demande sur les 30 derniers jours : vérifiez que la bulle de l'assistant apparaît sur son site"
                >
                  <UIcon name="i-lucide-triangle-alert" class="h-3 w-3" />
                  Risque de désabonnement
                </span>
                <span class="app-badge" :class="STATUS_BADGES[assistant.status] ?? ''">
                  {{ statusLabel(assistant) }}
                </span>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-1">
              <span
                v-for="language in assistant.languages"
                :key="language"
                class="rounded border border-[var(--app-line)] px-1.5 py-0.5 text-[10px] tracking-wide text-[var(--app-ink-soft)] uppercase"
              >
                {{ language }}
              </span>
              <span
                v-if="assistant.requests_30d > 0"
                class="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink-soft)] tabular-nums"
                :title="requestCountsTitle(assistant)"
              >
                <UIcon name="i-lucide-inbox" class="h-3 w-3" />
                {{ assistant.requests_7d }} demande{{ assistant.requests_7d > 1 ? 's' : '' }} / 7 j ·
                {{ assistant.requests_30d }} / 30 j
              </span>
              <span
                v-if="assistant.requests_outside_hours_pct !== null"
                class="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink-soft)] tabular-nums"
                title="Part des demandes des 30 derniers jours arrivées en dehors des horaires d'ouverture"
              >
                <UIcon name="i-lucide-moon" class="h-3 w-3" />
                {{ assistant.requests_outside_hours_pct }} % hors horaires
              </span>
              <span
                v-if="assistant.conversations_7d > 0"
                class="inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-ink-soft)] tabular-nums"
                :class="{ 'ml-auto': assistant.requests_30d === 0 }"
              >
                <UIcon name="i-lucide-messages-square" class="h-3 w-3" />
                {{ assistant.conversations_7d }} conv. / 7 j
              </span>
            </div>

            <div class="flex flex-wrap items-center gap-2">
              <a
                :href="demoUrlWithInternal(assistant.demo_url)"
                target="_blank"
                rel="noopener noreferrer"
                class="btn-secondary h-8 text-xs"
              >
                <UIcon name="i-lucide-external-link" class="mr-1.5 h-3.5 w-3.5" />
                Voir la démo
              </a>
              <button type="button" class="btn-secondary h-8 text-xs" @click="openConversations(assistant)">
                <UIcon name="i-lucide-messages-square" class="mr-1.5 h-3.5 w-3.5" />
                Conversations
              </button>
              <button
                type="button"
                class="btn-secondary h-8 text-xs"
                title="Site, fiche Google et documents lus par l'assistant"
                @click="openSources(assistant)"
              >
                <UIcon name="i-lucide-library" class="mr-1.5 h-3.5 w-3.5" />
                Sources
              </button>
              <button type="button" class="btn-secondary h-8 text-xs" @click="copySnippet(assistant)">
                <UIcon name="i-lucide-code" class="mr-1.5 h-3.5 w-3.5" />
                Copier le script
              </button>
              <button type="button" class="btn-secondary h-8 text-xs" @click="openSettings(assistant)">
                <UIcon name="i-lucide-pencil" class="mr-1.5 h-3.5 w-3.5" />
                Personnaliser
              </button>
              <button
                type="button"
                class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="regeneratingId === assistant.id"
                @click="regenerateAssistant(assistant)"
              >
                <UIcon
                  :name="regeneratingId === assistant.id ? 'i-lucide-loader-circle' : 'i-lucide-refresh-cw'"
                  class="mr-1.5 h-3.5 w-3.5"
                  :class="{ 'animate-spin': regeneratingId === assistant.id }"
                />
                Régénérer
              </button>
              <button
                v-if="assistant.status === 'delivered'"
                type="button"
                class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                :disabled="clientLinkBusyId === assistant.id"
                title="Email au commerçant avec le lien de son espace (demandes, rapport, réglages, abonnement)"
                @click="askSendClientSpace(assistant)"
              >
                <UIcon
                  :name="clientLinkBusyId === assistant.id ? 'i-lucide-loader-circle' : 'i-lucide-user-round-key'"
                  class="mr-1.5 h-3.5 w-3.5"
                  :class="{ 'animate-spin': clientLinkBusyId === assistant.id }"
                />
                Envoyer l'espace client
              </button>
              <button
                v-if="confirmingId !== assistant.id"
                type="button"
                class="text-muted ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs transition-colors hover:text-[var(--app-red)]"
                @click="confirmingId = assistant.id"
              >
                <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
                Supprimer
              </button>
              <button
                v-else
                type="button"
                class="ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg bg-[var(--app-red)] px-2.5 text-xs font-medium text-white"
                @click="removeAssistant(assistant)"
              >
                <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
                Confirmer
              </button>
            </div>

            <code
              class="block truncate rounded-md bg-[var(--app-surface-2)] px-2 py-1.5 text-[11px] text-[var(--app-ink-soft)]"
            >
              {{ assistant.embed_snippet }}
            </code>

            <div class="flex flex-wrap items-center gap-2 border-t border-[var(--app-line-soft)] pt-3">
              <span class="text-muted text-[10px] font-semibold tracking-wide uppercase">Vidéo</span>
              <template v-if="assistant.video_status === 'ready'">
                <a
                  :href="assistant.video_page_url ?? '#'"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="btn-secondary h-8 text-xs"
                >
                  <UIcon name="i-lucide-play" class="mr-1.5 h-3.5 w-3.5" />
                  Voir la vidéo
                </a>
                <button type="button" class="btn-secondary h-8 text-xs" @click="copyVideoLink(assistant)">
                  <UIcon name="i-lucide-link" class="mr-1.5 h-3.5 w-3.5" />
                  Copier le lien
                </button>
                <button
                  type="button"
                  class="text-muted ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs transition-colors hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="videoBusyId === assistant.id"
                  @click="generateVideo(assistant)"
                >
                  <UIcon
                    :name="videoBusyId === assistant.id ? 'i-lucide-loader-circle' : 'i-lucide-refresh-cw'"
                    class="h-3.5 w-3.5"
                    :class="{ 'animate-spin': videoBusyId === assistant.id }"
                  />
                  Régénérer
                </button>
              </template>
              <span
                v-else-if="assistant.video_status === 'pending' || assistant.video_status === 'generating'"
                class="text-muted inline-flex items-center gap-1.5 text-xs"
              >
                <UIcon name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
                Génération en cours…
              </span>
              <template v-else>
                <button
                  type="button"
                  class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="videoBusyId === assistant.id"
                  @click="generateVideo(assistant)"
                >
                  <UIcon
                    :name="videoBusyId === assistant.id ? 'i-lucide-loader-circle' : 'i-lucide-clapperboard'"
                    class="mr-1.5 h-3.5 w-3.5"
                    :class="{ 'animate-spin': videoBusyId === assistant.id }"
                  />
                  Générer la vidéo
                </button>
                <span
                  v-if="assistant.video_status === 'failed'"
                  class="text-[11px] text-[var(--app-red)]"
                  :title="assistant.video_error ?? ''"
                >
                  échec, réessayer
                </span>
              </template>
            </div>

            <div class="flex flex-wrap items-center gap-2 border-t border-[var(--app-line-soft)] pt-3">
              <span class="text-muted text-[10px] font-semibold tracking-wide uppercase">Abonnement</span>
              <span v-if="assistant.subscription_status === 'active'" class="app-badge app-badge--success">
                <UIcon name="i-lucide-check" class="h-3 w-3" />
                Abonné · {{ subscriptionLabel(assistant) }}
              </span>
              <span v-else-if="assistant.status === 'delivered'" class="text-muted text-xs">
                Vendu sans abonnement Stripe
              </span>
              <template v-else>
                <button
                  type="button"
                  class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="subscriptionBusyId === assistant.id"
                  @click="copySubscriptionLink(assistant, 'month')"
                >
                  <UIcon
                    :name="subscriptionBusyId === assistant.id ? 'i-lucide-loader-circle' : 'i-lucide-link'"
                    class="mr-1.5 h-3.5 w-3.5"
                    :class="{ 'animate-spin': subscriptionBusyId === assistant.id }"
                  />
                  Lien mensuel
                </button>
                <button
                  type="button"
                  class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                  :disabled="subscriptionBusyId === assistant.id"
                  @click="copySubscriptionLink(assistant, 'year')"
                >
                  <UIcon name="i-lucide-link" class="mr-1.5 h-3.5 w-3.5" />
                  Lien annuel
                </button>
              </template>
            </div>
          </article>
        </div>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex flex-wrap items-end justify-between gap-2 border-b border-[var(--app-line)]">
          <h2 class="pb-2 text-sm font-semibold text-[var(--app-ink)]">Demandes</h2>
          <UiFilterTabs v-model="requestFilter" :tabs="requestFilterTabs" />
        </div>

        <UiEmptyState
          v-if="visibleRequests.length === 0"
          :title="requestFilter === 'new' ? 'Aucune demande à traiter' : 'Aucune demande pour le moment'"
          description="Chaque visiteur qui laisse ses coordonnées dans un assistant apparaît ici."
        />

        <template v-else>
          <ul class="app-card divide-y divide-[var(--app-line-soft)] overflow-hidden">
            <li v-for="request in visibleRequests" :key="request.id" class="flex flex-col gap-2 px-4 py-3">
              <div class="flex flex-wrap items-center gap-1.5">
                <span class="app-badge" :class="request.type === 'urgent' ? 'app-badge--danger' : ''">
                  {{ REQUEST_TYPE_LABELS[request.type] }}
                </span>
                <span v-if="request.received_outside_hours" class="app-badge">
                  <UIcon name="i-lucide-moon" class="h-3 w-3" />
                  Hors horaires
                </span>
                <span v-if="request.photo_urls.length > 0" class="app-badge">
                  <UIcon name="i-lucide-camera" class="h-3 w-3" />
                  {{ request.photo_urls.length }} photo{{ request.photo_urls.length > 1 ? 's' : '' }}
                </span>
                <span
                  v-if="request.is_test"
                  class="app-badge"
                  title="Laissée pendant une visite de test de l'opérateur"
                >
                  Test
                </span>
                <span v-if="request.status === 'handled'" class="app-badge app-badge--success">Traitée</span>
                <span v-else-if="request.status === 'dropped'" class="app-badge">Sans suite</span>
                <span class="text-muted ml-auto text-xs tabular-nums">
                  {{ request.business_name }} · {{ formatShortMonthDayTime(request.created_at) }}
                </span>
              </div>
              <div class="flex flex-col gap-2 @xl:flex-row @xl:items-start @xl:gap-4">
                <div class="min-w-0 shrink-0 @xl:w-56">
                  <p class="text-sm font-medium text-[var(--app-ink)]">{{ request.name }}</p>
                  <a
                    v-if="contactHref(request.contact)"
                    :href="contactHref(request.contact) ?? undefined"
                    class="text-muted text-xs break-all underline-offset-2 hover:text-[var(--app-ink)] hover:underline"
                  >
                    {{ request.contact }}
                  </a>
                  <p v-else class="text-muted text-xs break-all">{{ request.contact }}</p>
                </div>
                <div class="flex min-w-0 flex-1 flex-col gap-2">
                  <p class="text-xs leading-relaxed text-[var(--app-ink-soft)] @xl:text-sm">
                    {{ request.need_summary || request.need || 'Demande de rappel, sans détail.' }}
                  </p>
                  <p
                    v-if="request.appointment_booked"
                    class="flex items-start gap-1.5 text-xs leading-relaxed text-[var(--app-ink)]"
                  >
                    <UIcon name="i-lucide-calendar-check" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>Rendez-vous réservé dans l'agenda du client : {{ request.appointment_booked }}</span>
                  </p>
                  <p
                    v-else-if="request.appointment_slots.length > 0"
                    class="flex items-start gap-1.5 text-xs leading-relaxed text-[var(--app-ink)]"
                  >
                    <UIcon name="i-lucide-calendar-days" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    <span>Créneaux souhaités (à confirmer) : {{ request.appointment_slots.join(' ou ') }}</span>
                  </p>
                  <div v-if="request.photo_urls.length > 0" class="flex flex-wrap gap-1.5">
                    <a
                      v-for="(url, index) in request.photo_urls"
                      :key="url"
                      :href="url"
                      target="_blank"
                      rel="noopener"
                      class="block h-12 w-12 overflow-hidden rounded-md border border-[var(--app-line)]"
                      :aria-label="`Photo ${index + 1} envoyée par ${request.name}`"
                    >
                      <img :src="url" alt="" loading="lazy" class="h-full w-full object-cover" />
                    </a>
                  </div>
                </div>
                <div class="flex shrink-0 items-center gap-2">
                  <template v-if="request.status === 'new'">
                    <button
                      type="button"
                      class="btn-secondary h-8 text-xs disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="requestBusyId === request.id"
                      @click="setRequestStatus(request, 'handled')"
                    >
                      <UIcon name="i-lucide-check" class="mr-1 h-3.5 w-3.5" />
                      Marquer traitée
                    </button>
                    <button
                      type="button"
                      class="text-muted h-9 cursor-pointer px-1 text-xs transition-colors hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                      :disabled="requestBusyId === request.id"
                      @click="setRequestStatus(request, 'dropped')"
                    >
                      Sans suite
                    </button>
                  </template>
                  <button
                    v-else
                    type="button"
                    class="text-muted h-9 cursor-pointer px-1 text-xs transition-colors hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-50"
                    :disabled="requestBusyId === request.id"
                    @click="setRequestStatus(request, 'new')"
                  >
                    Rouvrir
                  </button>
                  <button
                    v-if="request.prospect_id !== null"
                    type="button"
                    class="text-muted flex h-9 w-9 cursor-pointer items-center justify-center rounded-md transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                    :aria-label="`Ouvrir le prospect ${request.business_name}`"
                    @click="openRequestProspect(request)"
                  >
                    <UIcon name="i-lucide-arrow-up-right" class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </li>
          </ul>
          <p v-if="requestFilter === 'all' && requests.length >= REQUEST_LIST_LIMIT" class="text-muted text-xs">
            Les {{ REQUEST_LIST_LIMIT }} dernières demandes sont affichées ; l'onglet « À traiter » les montre toutes.
          </p>
        </template>
      </section>
    </template>

    <UiConfirmModal
      ref="clientSpaceConfirmModal"
      title="Envoyer l'espace client"
      :message="clientSpaceConfirmMessage"
      confirm-text="Envoyer"
      cancel-text="Annuler"
      confirm-button-variant="primary"
      @confirm="sendClientSpace"
    />
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { AiAssistantService } from '~/services/aiAssistantService'
import { AssistantSidecarService } from '~/services/assistantSidecarService'
import { ProspectsService } from '~/services/prospectsService'
import type {
  AiAssistantClientLink,
  AiAssistantListResponse,
  AiAssistantRequestItem,
  AiAssistantRequestsResponse,
  AiAssistantRequestStatus,
  AiAssistantRequestType,
  AiAssistantSummary,
} from '~/types/AiAssistant'
import type { AssistantMutationNotice } from '~/types/DrawerStack'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import type { Prospect } from '~/types'
import type { UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { contactHref } from '~/utils/contactLink'
import { daysUntil, formatShortMonthDayTime, parseApiDate } from '~/utils/date'

/**
 * Management page for the AI assistant module: the generated assistants (demo link + embed
 * snippet) and the requests their visitors left. Generation itself happens from a prospect;
 * customization happens in the settings drawer of the stack.
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

useSeoMeta({ title: 'Assistants IA — DevLeadHunter' })

const toast: UseToastReturn = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

/** How many requests the API lists at most per call; « À traiter » is fetched apart so it is never cut. */
const REQUEST_LIST_LIMIT: number = 300

const assistants: Ref<AiAssistantSummary[]> = ref([])
/** The latest requests, every status (at most REQUEST_LIST_LIMIT). */
const requests: Ref<AiAssistantRequestItem[]> = ref([])
/** The requests still new, fetched apart so the tab shows them all. */
const newRequests: Ref<AiAssistantRequestItem[]> = ref([])
/** Real requests still waiting for handling (tests excluded), as counted by the API. */
const pendingRequestCount: Ref<number> = ref(0)
const requestFilter: Ref<string> = ref('new')
const requestBusyId: Ref<number | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const hasLoadFailed: Ref<boolean> = ref(false)
const confirmingId: Ref<number | null> = ref(null)
const regeneratingId: Ref<number | null> = ref(null)
const clientLinkBusyId: Ref<number | null> = ref(null)
/** The sold assistant whose client-space email waits for the confirmation. */
const clientSpaceTarget: Ref<AiAssistantSummary | null> = ref(null)
const clientSpaceConfirmModal: Ref<{ open: () => void } | null> = ref(null)
const videoBusyId: Ref<number | null> = ref(null)
const videoPollTimer: Ref<ReturnType<typeof setInterval> | null> = ref(null)
const subscriptionBusyId: Ref<number | null> = ref(null)

const STATUS_LABELS: Record<string, string> = {
  pending: 'En préparation',
  provisioning: 'En préparation',
  active: 'Actif',
  unavailable: 'Indisponible',
  expired: 'Expiré',
  failed: 'Échec',
  delivered: 'Vendu',
}

/** Colour is kept for the statuses: live demos and sold assistants read at a glance. */
const STATUS_BADGES: Record<string, string> = {
  active: 'app-badge--success',
  delivered: 'app-badge--strong',
  failed: 'app-badge--danger',
}

const REQUEST_TYPE_LABELS: Record<AiAssistantRequestType, string> = {
  question: 'Question',
  quote: 'Devis',
  appointment: 'Rendez-vous',
  urgent: 'Urgence',
  other: 'Autre',
}

/** Assistants currently live (the headline module KPI). */
const activeAssistantCount: ComputedRef<number> = computed(
  (): number => assistants.value.filter((item: AiAssistantSummary): boolean => item.status === 'active').length,
)

/** Short date of the most recent request, or an em dash when none. */
const latestRequestLabel: ComputedRef<string> = computed((): string => {
  const latest: AiAssistantRequestItem | undefined = requests.value.find(
    (request: AiAssistantRequestItem): boolean => !request.is_test,
  )
  return latest ? formatDate(latest.created_at) : '—'
})

/** Requests still waiting for the owner (tests left from internal visits only show under « Toutes »). */
const pendingRequests: ComputedRef<AiAssistantRequestItem[]> = computed((): AiAssistantRequestItem[] =>
  newRequests.value.filter((request: AiAssistantRequestItem): boolean => !request.is_test),
)

const requestFilterTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] => [
  { key: 'new', label: 'À traiter', count: pendingRequestCount.value },
  { key: 'all', label: 'Toutes', count: requests.value.length },
])

const visibleRequests: ComputedRef<AiAssistantRequestItem[]> = computed((): AiAssistantRequestItem[] =>
  requestFilter.value === 'new' ? pendingRequests.value : requests.value,
)

/** Whether any assistant is mid-generation, which keeps the list polling. */
const hasGeneratingVideo: ComputedRef<boolean> = computed((): boolean =>
  assistants.value.some(
    (item: AiAssistantSummary): boolean => item.video_status === 'pending' || item.video_status === 'generating',
  ),
)

/** What the client-space confirmation asks, naming the address the email goes to. */
const clientSpaceConfirmMessage: ComputedRef<string> = computed((): string => {
  const target: AiAssistantSummary | null = clientSpaceTarget.value
  if (!target) return ''
  const recipient: string = target.email ? ` à ${target.email}` : ' à l’adresse connue du commerce'
  return `Envoyer au commerçant${recipient} le lien de son espace (demandes, rapport, réglages, abonnement) ? Le lien est aussi copié.`
})

/**
 * Tooltip detailing an assistant's request counts.
 * @param assistant - The assistant.
 * @returns A one-line explanation of the 7 / 30 day counts.
 */
function requestCountsTitle(assistant: AiAssistantSummary): string {
  return `${assistant.requests_7d} demande(s) sur 7 jours, ${assistant.requests_30d} sur 30 jours (tests exclus)`
}

/**
 * Append the internal marker so opening a demo from the dashboard never pollutes its analytics.
 * @param demoUrl - The assistant's public demo URL.
 * @returns The URL carrying `?internal=1`.
 */
function demoUrlWithInternal(demoUrl: string): string {
  return demoUrl.includes('?') ? `${demoUrl}&internal=1` : `${demoUrl}?internal=1`
}

/**
 * Open the journal of what this assistant's visitors asked (the 20 latest conversations).
 * @param assistant - The assistant whose conversations to read.
 */
function openConversations(assistant: AiAssistantSummary): void {
  drawerStack.push({ kind: 'assistant-conversations', assistant })
}

/**
 * Open what this assistant reads: its website pages, its Google listing, its documents (switches, upload).
 * @param assistant - The assistant whose sources to show.
 */
function openSources(assistant: AiAssistantSummary): void {
  drawerStack.push({ kind: 'assistant-sources', assistant })
}

/**
 * Open the settings drawer: identity, alerts to the business, model constraints.
 * @param assistant - The assistant to edit.
 */
function openSettings(assistant: AiAssistantSummary): void {
  drawerStack.push({ kind: 'assistant-settings', assistant })
}

/**
 * Open a request's prospect in the shared drawer, to act on it (call, add to a campaign…).
 * @param request - The request.
 * @returns A promise resolved once the prospect drawer is pushed.
 */
async function openRequestProspect(request: AiAssistantRequestItem): Promise<void> {
  if (request.prospect_id === null) return
  try {
    const prospect: Prospect = await ProspectsService.getProspect(request.prospect_id)
    drawerStack.push({ kind: 'prospect', prospect })
  } catch {
    toast.error('Prospect introuvable.')
  }
}

/**
 * Move a request to another status (handled, dropped, or back to new) and refresh its row in both lists.
 * @param request - The request to update.
 * @param status - Its new status.
 * @returns A promise resolved once the update is saved.
 */
async function setRequestStatus(request: AiAssistantRequestItem, status: AiAssistantRequestStatus): Promise<void> {
  requestBusyId.value = request.id
  try {
    const updated: AiAssistantRequestItem = await AiAssistantService.updateRequest(request.id, { status })
    requests.value = requests.value.map(
      (item: AiAssistantRequestItem): AiAssistantRequestItem => (item.id === updated.id ? updated : item),
    )
    const others: AiAssistantRequestItem[] = newRequests.value.filter(
      (item: AiAssistantRequestItem): boolean => item.id !== updated.id,
    )
    newRequests.value = updated.status === 'new' ? [updated, ...others] : others
    if (!request.is_test) {
      const wasPending: boolean = request.status === 'new'
      const isPending: boolean = updated.status === 'new'
      pendingRequestCount.value += Number(isPending) - Number(wasPending)
    }
  } catch {
    toast.error('Mise à jour de la demande impossible.')
  } finally {
    requestBusyId.value = null
  }
}

/**
 * Format an API timestamp as a short local date.
 * @param iso - The API date string (UTC, naive).
 * @returns The localised « jour mois » label.
 */
function formatDate(iso: string): string {
  return parseApiDate(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })
}

/**
 * Copy an assistant's embed snippet to the clipboard.
 * @param assistant - The assistant whose snippet to copy.
 * @returns A promise resolved once the copy is attempted.
 */
async function copySnippet(assistant: AiAssistantSummary): Promise<void> {
  try {
    await navigator.clipboard.writeText(assistant.embed_snippet)
    toast.success('Script copié : à coller avant </body> du site du client.')
  } catch {
    toast.error('Copie impossible depuis ce navigateur.')
  }
}

/**
 * Ask before emailing the business its client-space link: the email leaves at once when confirmed.
 * @param assistant - A sold assistant.
 */
function askSendClientSpace(assistant: AiAssistantSummary): void {
  clientSpaceTarget.value = assistant
  clientSpaceConfirmModal.value?.open()
}

/**
 * Email the business its client-space link (requests, report, settings, subscription) and copy the link.
 * @returns A promise resolved once sent (or refused) and copied.
 */
async function sendClientSpace(): Promise<void> {
  const assistant: AiAssistantSummary | null = clientSpaceTarget.value
  if (!assistant) return
  clientLinkBusyId.value = assistant.id
  try {
    const link: AiAssistantClientLink = await AiAssistantService.issueClientLink(assistant.id, true)
    let copied: boolean = true
    try {
      await navigator.clipboard.writeText(link.url)
    } catch {
      copied = false
    }
    const copyNote: string = copied ? ' Lien copié.' : ''
    if (link.sent_to) {
      toast.success(`Espace client envoyé à ${link.sent_to}.${copyNote}`)
    } else {
      const reason: string = (link.send_error ?? 'raison inconnue').replace(/\.+$/, '')
      toast.error(`Email non envoyé : ${reason}.${copyNote}`)
    }
  } catch {
    toast.error("Lien de l'espace client indisponible pour l'instant.")
  } finally {
    clientLinkBusyId.value = null
    clientSpaceTarget.value = null
  }
}

/**
 * Soft-delete an assistant after the inline confirmation, and take its requests and drawers off the screen.
 * @param assistant - The assistant to remove.
 * @returns A promise resolved once removed and the lists refreshed.
 */
async function removeAssistant(assistant: AiAssistantSummary): Promise<void> {
  confirmingId.value = null
  try {
    await AiAssistantService.remove(assistant.id)
    assistants.value = assistants.value.filter((item: AiAssistantSummary): boolean => item.id !== assistant.id)
    const removedPending: number = pendingRequests.value.filter(
      (item: AiAssistantRequestItem): boolean => item.assistant_id === assistant.id,
    ).length
    requests.value = requests.value.filter(
      (item: AiAssistantRequestItem): boolean => item.assistant_id !== assistant.id,
    )
    newRequests.value = newRequests.value.filter(
      (item: AiAssistantRequestItem): boolean => item.assistant_id !== assistant.id,
    )
    pendingRequestCount.value = Math.max(pendingRequestCount.value - removedPending, 0)
    drawerStack.notifyAssistantDeleted(assistant.id)
    toast.success('Assistant supprimé.')
  } catch {
    toast.error("Suppression impossible pour l'instant.")
  }
}

/**
 * Rebuild an assistant's knowledge from its prospect's latest data, keeping its branding and link.
 * @param assistant - The assistant to regenerate.
 * @returns A promise resolved once regenerated and the card refreshed.
 */
async function regenerateAssistant(assistant: AiAssistantSummary): Promise<void> {
  if (regeneratingId.value !== null) return
  regeneratingId.value = assistant.id
  try {
    const updated: AiAssistantSummary = await AiAssistantService.regenerate(assistant.id)
    patchAssistant(updated)
    toast.success('Assistant régénéré depuis les dernières données du prospect.')
  } catch {
    toast.error('Régénération impossible pour le moment.')
  } finally {
    regeneratingId.value = null
  }
}

/** Poll the list every few seconds while a video is generating, without hiding the page, then stop. */
function startVideoPolling(): void {
  if (videoPollTimer.value !== null) return
  videoPollTimer.value = setInterval((): void => {
    if (!hasGeneratingVideo.value) {
      stopVideoPolling()
      return
    }
    void refreshAssistants()
  }, 5000)
}

/** Stop the video-generation poll. */
function stopVideoPolling(): void {
  if (videoPollTimer.value !== null) {
    clearInterval(videoPollTimer.value)
    videoPollTimer.value = null
  }
}

/**
 * Start (or restart) generating the assistant's prospection video.
 * @param assistant - The assistant to make a video for.
 * @returns A promise resolved once the generation is requested.
 */
async function generateVideo(assistant: AiAssistantSummary): Promise<void> {
  if (videoBusyId.value !== null) return
  videoBusyId.value = assistant.id
  try {
    // Desktop-first (like the site video): build the whole clip on the user's PC — the sidecar records
    // the widget answering and montages it with the bundled ffmpeg, sparing the shared VPS. Off the
    // desktop (web build) or on any local failure, fall back to the server-side generation.
    const build: Awaited<ReturnType<typeof AssistantSidecarService.buildFullVideo>> =
      await AssistantSidecarService.buildFullVideo(assistant.id)
    if (build.status === 'done' && build.assistant) {
      patchAssistant(build.assistant)
      toast.success('Vidéo générée sur votre ordinateur.')
      return
    }
    if (build.status === 'failed') {
      toast.info('Génération locale indisponible, bascule sur le serveur…')
    }

    // 'unavailable' (web build, no sidecar) or 'failed' → server-side generation (memory-guarded).
    const updated: AiAssistantSummary = await AiAssistantService.generateVideo(assistant.id)
    patchAssistant(updated)
    toast.success('Génération de la vidéo lancée.')
    startVideoPolling()
  } catch {
    toast.error("Vidéo impossible : enregistrez d'abord votre clip webcam « assistant » dans les paramètres.")
  } finally {
    videoBusyId.value = null
  }
}

/**
 * Replace one assistant in the list with an updated copy (in place).
 * @param updated - The assistant whose card should reflect the new state.
 */
function patchAssistant(updated: AiAssistantSummary): void {
  assistants.value = assistants.value.map(
    (item: AiAssistantSummary): AiAssistantSummary => (item.id === updated.id ? updated : item),
  )
}

/**
 * Copy an assistant's video page link to the clipboard.
 * @param assistant - The assistant whose video link to copy.
 * @returns A promise resolved once the copy is attempted.
 */
async function copyVideoLink(assistant: AiAssistantSummary): Promise<void> {
  if (!assistant.video_page_url) return
  try {
    await navigator.clipboard.writeText(assistant.video_page_url)
    toast.success('Lien vidéo copié.')
  } catch {
    toast.error('Copie impossible depuis ce navigateur.')
  }
}

/**
 * Copy the permanent subscription link to send to the client (each click opens a fresh Stripe Checkout).
 * @param assistant - The assistant being sold.
 * @param interval - `month` (mensuel) or `year` (annuel).
 * @returns A promise resolved once the link is copied.
 */
async function copySubscriptionLink(assistant: AiAssistantSummary, interval: 'month' | 'year'): Promise<void> {
  if (subscriptionBusyId.value !== null) return
  subscriptionBusyId.value = assistant.id
  try {
    const { url }: { url: string } = await AiAssistantService.getSubscriptionLink(assistant.id, interval)
    await navigator.clipboard.writeText(url)
    toast.success(
      `Lien d'abonnement ${interval === 'year' ? 'annuel' : 'mensuel'} copié : envoyez-le au client, il reste valable.`,
    )
  } catch {
    toast.error('Lien indisponible pour cet assistant.')
  } finally {
    subscriptionBusyId.value = null
  }
}

/**
 * Human label for an assistant's active subscription (e.g. « 79 €/mois »).
 * @param assistant - The subscribed assistant.
 * @returns The formatted price + interval, or an empty string when there is none.
 */
function subscriptionLabel(assistant: AiAssistantSummary): string {
  if (assistant.subscription_amount_cents == null) return ''
  const euros: number = Math.round(assistant.subscription_amount_cents / 100)
  return `${euros} €/${assistant.subscription_interval === 'year' ? 'an' : 'mois'}`
}

/**
 * Text of the status badge.
 * @param assistant - The assistant.
 * @returns The French label of the status, or the raw status for an unknown one.
 */
function statusLabel(assistant: AiAssistantSummary): string {
  return STATUS_LABELS[assistant.status] ?? assistant.status
}

/**
 * Where the demo stands in its life: waiting for its first send, or counting down to its expiry.
 * @param assistant - The assistant.
 * @returns « En attente d'envoi », « Expire dans N j », or an empty string once the demo is sold or gone.
 */
function demoLifetimeLabel(assistant: AiAssistantSummary): string {
  if (assistant.status !== 'active') return ''
  if (!assistant.demo_link_sent_at || !assistant.expires_at) return "En attente d'envoi"
  return `Expire dans ${daysUntil(assistant.expires_at)} j`
}

/**
 * Refresh the assistant cards only (video progress), leaving the page and the requests as they are.
 * @returns A promise resolved once the cards are refreshed.
 */
async function refreshAssistants(): Promise<void> {
  try {
    const list: AiAssistantListResponse = await AiAssistantService.list()
    assistants.value = list.assistants
  } catch {
    // A missed poll is not worth a toast every five seconds: the next one, or a reload, catches up.
  }
}

/**
 * Load the assistants and the requests their visitors left: the latest ones, and every one still new.
 * @returns A promise resolved once loaded.
 */
async function loadData(): Promise<void> {
  isLoading.value = true
  hasLoadFailed.value = false
  try {
    const [assistantList, requestList, newList]: [
      AiAssistantListResponse,
      AiAssistantRequestsResponse,
      AiAssistantRequestsResponse,
    ] = await Promise.all([
      AiAssistantService.list(),
      AiAssistantService.listRequests(),
      AiAssistantService.listRequests('new'),
    ])
    assistants.value = assistantList.assistants
    requests.value = requestList.requests
    newRequests.value = newList.requests
    pendingRequestCount.value = requestList.pending_count
  } catch {
    hasLoadFailed.value = true
  } finally {
    isLoading.value = false
  }
}

watch(
  (): number => drawerStack.assistantMutationCounter,
  (): void => {
    const notice: AssistantMutationNotice | null = drawerStack.lastAssistantMutation
    if (notice?.type === 'updated') patchAssistant(notice.assistant)
  },
)

onMounted(async (): Promise<void> => {
  await loadData()
  if (hasGeneratingVideo.value) startVideoPolling()
})

onUnmounted((): void => {
  stopVideoPolling()
})
</script>
