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

    <div v-if="isLoading" class="flex h-40 items-center justify-center">
      <UIcon name="i-lucide-loader-circle" class="h-7 w-7 animate-spin text-[var(--app-ink-soft)]" />
    </div>

    <template v-else>
      <div class="grid grid-cols-3 gap-3">
        <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
          <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ activeAssistantCount }}</p>
          <p class="text-muted text-[10px] tracking-wide uppercase">Assistants actifs</p>
        </div>
        <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
          <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ pendingRequestCount }}</p>
          <p class="text-muted text-[10px] tracking-wide uppercase">Demandes à traiter</p>
        </div>
        <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5 text-center">
          <p class="text-xl font-bold text-[var(--app-ink)] tabular-nums">{{ latestRequestLabel }}</p>
          <p class="text-muted text-[10px] tracking-wide uppercase">Dernière demande</p>
        </div>
      </div>

      <section class="flex flex-col gap-3">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Mes assistants</h2>
          <span class="text-muted text-xs tabular-nums">{{ assistants.length }}</span>
        </div>

        <div v-if="assistants.length === 0" class="app-card flex flex-col items-center gap-4 px-6 py-10 text-center">
          <UIcon name="i-lucide-bot" class="h-8 w-8 text-[var(--app-faint)]" />
          <p class="text-muted max-w-sm text-sm leading-relaxed">
            Aucun assistant généré. Ouvrez un prospect et cliquez « Générer un assistant IA » pour créer sa démo.
          </p>
          <NuxtLink to="/dashboard/my-prospects" class="btn-secondary h-9 text-xs">
            <UIcon name="i-lucide-users" class="mr-1.5 h-4 w-4" />
            Voir mes prospects
          </NuxtLink>
        </div>

        <div v-else class="grid gap-3 @2xl:grid-cols-2">
          <article v-for="assistant in assistants" :key="assistant.id" class="app-card flex min-w-0 flex-col gap-3 p-4">
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate text-sm font-semibold text-[var(--app-ink)]">{{ assistant.business_name }}</p>
                <p class="text-muted truncate text-xs">
                  {{ assistant.assistant_name
                  }}<span v-if="demoLifetimeLabel(assistant)"> · {{ demoLifetimeLabel(assistant) }}</span>
                </p>
              </div>
              <span
                class="shrink-0 rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide uppercase"
                :class="
                  assistant.status === 'active'
                    ? 'border-[var(--app-green)] text-[var(--app-green)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)]'
                "
              >
                {{ statusLabel(assistant) }}
              </span>
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
                class="ml-auto inline-flex items-center gap-1 text-[11px] font-medium text-[var(--app-green)] tabular-nums"
                :title="requestCountsTitle(assistant)"
              >
                <UIcon name="i-lucide-inbox" class="h-3 w-3" />
                {{ assistant.requests_7d }} dem. / 7 j · {{ assistant.requests_30d }} / 30 j
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
              <button type="button" class="btn-secondary h-8 text-xs" @click="copySnippet(assistant)">
                <UIcon name="i-lucide-code" class="mr-1.5 h-3.5 w-3.5" />
                Copier le script
              </button>
              <button type="button" class="btn-secondary h-8 text-xs" @click="openEdit(assistant)">
                <UIcon name="i-lucide-pencil" class="mr-1.5 h-3.5 w-3.5" />
                Personnaliser
              </button>
              <button
                type="button"
                class="btn-secondary h-8 text-xs"
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
                  class="text-muted ml-auto flex h-8 cursor-pointer items-center gap-1 rounded-lg px-2 text-xs transition-colors hover:text-[var(--app-ink)]"
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
                  class="btn-secondary h-8 text-xs"
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
                  échec — réessayer
                </span>
              </template>
            </div>

            <div class="flex flex-wrap items-center gap-2 border-t border-[var(--app-line-soft)] pt-3">
              <span class="text-muted text-[10px] font-semibold tracking-wide uppercase">Abonnement</span>
              <span
                v-if="assistant.subscription_status === 'active'"
                class="inline-flex items-center gap-1 rounded-full border border-[var(--app-green)] px-2 py-0.5 text-[10px] font-medium text-[var(--app-green)]"
              >
                <UIcon name="i-lucide-check" class="h-3 w-3" />
                Abonné · {{ subscriptionLabel(assistant) }}
              </span>
              <button
                type="button"
                class="btn-secondary h-8 text-xs"
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
                class="btn-secondary h-8 text-xs"
                :disabled="subscriptionBusyId === assistant.id"
                @click="copySubscriptionLink(assistant, 'year')"
              >
                <UIcon name="i-lucide-link" class="mr-1.5 h-3.5 w-3.5" />
                Lien annuel
              </button>
            </div>
          </article>
        </div>
      </section>

      <section class="flex flex-col gap-3">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Demandes</h2>
          <UiFilterTabs v-model="requestFilter" :tabs="requestFilterTabs" />
        </div>

        <div v-if="visibleRequests.length === 0" class="app-card px-6 py-8 text-center">
          <p class="text-muted text-sm leading-relaxed">
            {{
              requestFilter === 'new'
                ? 'Aucune demande à traiter. Chaque visiteur qui laisse ses coordonnées dans un assistant apparaît ici.'
                : 'Aucune demande pour le moment. Chaque visiteur qui laisse ses coordonnées dans un assistant apparaît ici.'
            }}
          </p>
        </div>

        <ul v-else class="app-card divide-y divide-[var(--app-line-soft)] overflow-hidden">
          <li v-for="request in visibleRequests" :key="request.id" class="flex flex-col gap-2 px-4 py-3">
            <div class="flex flex-wrap items-center gap-1.5">
              <span class="app-badge" :class="REQUEST_TYPE_BADGES[request.type]">
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
              <span v-if="request.is_test" class="app-badge" title="Laissée depuis une visite interne (?internal=1)">
                Test
              </span>
              <span v-if="request.status === 'handled'" class="app-badge app-badge--success">Traitée</span>
              <span v-else-if="request.status === 'dropped'" class="app-badge">Sans suite</span>
              <span class="text-muted ml-auto text-xs tabular-nums">
                {{ request.business_name }} · {{ formatDateTime(request.created_at) }}
              </span>
            </div>
            <div class="flex flex-col gap-2 @xl:flex-row @xl:items-start @xl:gap-4">
              <div class="min-w-0 shrink-0 @xl:w-48">
                <p class="truncate text-sm font-medium text-[var(--app-ink)]">{{ request.name }}</p>
                <p class="text-muted truncate text-xs">{{ request.contact }}</p>
              </div>
              <div class="flex min-w-0 flex-1 flex-col gap-2">
                <p class="text-xs leading-relaxed text-[var(--app-ink-soft)] @xl:text-sm">
                  {{ request.need_summary || request.need || 'Demande de rappel, sans détail.' }}
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
                    class="btn-secondary h-8 text-xs"
                    :disabled="requestBusyId === request.id"
                    @click="setRequestStatus(request, 'handled')"
                  >
                    <UIcon name="i-lucide-check" class="mr-1 h-3.5 w-3.5" />
                    Marquer traitée
                  </button>
                  <button
                    type="button"
                    class="text-muted h-8 cursor-pointer px-1 text-xs transition-colors hover:text-[var(--app-ink)]"
                    :disabled="requestBusyId === request.id"
                    @click="setRequestStatus(request, 'dropped')"
                  >
                    Sans suite
                  </button>
                </template>
                <button
                  v-else
                  type="button"
                  class="text-muted h-8 cursor-pointer px-1 text-xs transition-colors hover:text-[var(--app-ink)]"
                  :disabled="requestBusyId === request.id"
                  @click="setRequestStatus(request, 'new')"
                >
                  Rouvrir
                </button>
                <button
                  v-if="request.prospect_id !== null"
                  type="button"
                  class="text-muted flex h-7 w-7 cursor-pointer items-center justify-center rounded-md transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
                  :aria-label="`Ouvrir le prospect ${request.business_name}`"
                  @click="openRequestProspect(request)"
                >
                  <UIcon name="i-lucide-arrow-up-right" class="h-4 w-4" />
                </button>
              </div>
            </div>
          </li>
        </ul>
      </section>
    </template>

    <div
      v-if="editing"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] p-4"
      @click.self="closeEdit"
    >
      <div class="app-card max-h-[90vh] w-full max-w-md overflow-y-auto p-5">
        <div class="mb-4 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-[var(--app-ink)]">Personnaliser l'assistant</h3>
          <button
            type="button"
            class="text-muted cursor-pointer transition-colors hover:text-[var(--app-ink)]"
            aria-label="Fermer"
            @click="closeEdit"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="flex flex-col gap-3">
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Entreprise affichée</span>
            <input v-model="editForm.business_name" type="text" class="app-input" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Nom de l'assistant</span>
            <input v-model="editForm.assistant_name" type="text" class="app-input" placeholder="Sofia" />
          </label>
          <label class="flex flex-col gap-1">
            <span class="app-label !text-[0.6rem]">Ton</span>
            <input v-model="editForm.tone" type="text" class="app-input" placeholder="professionnel et chaleureux" />
          </label>

          <div class="flex flex-col gap-1.5">
            <span class="app-label !text-[0.6rem]">Langues</span>
            <div class="flex flex-wrap gap-1.5">
              <button
                v-for="language in LANGUAGE_OPTIONS"
                :key="language.code"
                type="button"
                class="cursor-pointer rounded-full border px-2.5 py-1 text-xs transition-colors"
                :class="
                  editForm.languages.includes(language.code)
                    ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
                    : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
                "
                @click="toggleLanguage(language.code)"
              >
                {{ language.label }}
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between gap-3">
            <span class="app-label !text-[0.6rem]">Couleur d'accent</span>
            <div class="flex items-center gap-2">
              <input
                v-model="editForm.accent_color"
                type="color"
                class="h-8 w-10 cursor-pointer rounded border border-[var(--app-line)] bg-transparent"
                aria-label="Choisir la couleur d'accent"
              />
              <input v-model="editForm.accent_color" type="text" class="app-input w-28" placeholder="#c8862f" />
            </div>
          </div>

          <div class="flex flex-col gap-3 border-t border-[var(--app-line-soft)] pt-3">
            <div class="flex flex-col gap-0.5">
              <span class="text-xs font-semibold text-[var(--app-ink)]">Alertes au commerçant</span>
              <span class="text-muted text-xs leading-relaxed">
                Une fois l'assistant vendu : chaque demande par email, et un SMS pour celles qui ne peuvent pas
                attendre. Rappel le lendemain si elle n'est pas traitée.
              </span>
            </div>
            <label class="flex flex-col gap-1">
              <span class="app-label !text-[0.6rem]">Mobile du commerçant</span>
              <input
                v-model="editForm.alert_phone"
                type="tel"
                inputmode="tel"
                autocomplete="off"
                class="app-input"
                placeholder="06 12 34 56 78 ou +352 621 123 456"
              />
            </label>
            <UiSwitch id="assistant-alert-sms" v-model="editForm.alert_sms_enabled" label="SMS" />
            <template v-if="editForm.alert_sms_enabled">
              <div class="flex flex-col gap-1.5">
                <span class="app-label !text-[0.6rem]">SMS immédiat pour</span>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="option in ALERT_TYPE_OPTIONS"
                    :key="option.value"
                    type="button"
                    class="cursor-pointer rounded-full border px-2.5 py-1 text-xs transition-colors"
                    :class="
                      editForm.alert_sms_types.includes(option.value)
                        ? 'border-[var(--app-ink)] bg-[var(--app-ink)] text-[var(--app-bg)]'
                        : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
                    "
                    @click="toggleAlertType(option.value)"
                  >
                    {{ option.label }}
                  </button>
                </div>
              </div>
              <div class="flex flex-col gap-1.5">
                <span class="app-label !text-[0.6rem]">Ne pas déranger (SMS envoyés à la fin de la plage)</span>
                <div class="flex items-center gap-2 text-xs text-[var(--app-ink-soft)]">
                  <span>de</span>
                  <div class="w-24">
                    <UiSelectField v-model="editForm.alert_quiet_start_hour" :options="HOUR_OPTIONS" />
                  </div>
                  <span>à</span>
                  <div class="w-24">
                    <UiSelectField v-model="editForm.alert_quiet_end_hour" :options="HOUR_OPTIONS" />
                  </div>
                </div>
              </div>
            </template>
            <UiSwitch
              id="assistant-alert-email"
              v-model="editForm.alert_email_enabled"
              label="Email de résumé (toutes les demandes)"
            />
          </div>
        </div>

        <div class="mt-5 flex gap-2">
          <button type="button" class="btn-secondary flex-1" @click="closeEdit">Annuler</button>
          <button type="button" class="btn-primary flex-1" :disabled="isSaving" @click="saveEdit">
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            Enregistrer
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { AiAssistantService } from '~/services/aiAssistantService'
import { AssistantSidecarService } from '~/services/assistantSidecarService'
import { ProspectsService } from '~/services/prospectsService'
import type {
  AiAssistantAlertSettings,
  AiAssistantEditForm,
  AiAssistantListResponse,
  AiAssistantRequestItem,
  AiAssistantRequestsResponse,
  AiAssistantRequestStatus,
  AiAssistantRequestType,
  AiAssistantSummary,
  AiAssistantUpdatePayload,
} from '~/types/AiAssistant'
import type { SelectFieldOption } from '~/types/SelectField'
import type { UiFilterTab } from '~/types/UiFilterTabs'
import type { Prospect } from '~/types'
import type { UseToastReturn } from '~/types/Composables'
import { useToast } from '~/composables/useToast'
import { useDrawerStackStore } from '~/stores/drawerStack'
import { daysUntil, parseApiDate } from '~/utils/date'

/**
 * Management page for the AI assistant module: the generated assistants (demo link + embed
 * snippet) and the requests their visitors left. Generation itself happens from a prospect.
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

useSeoMeta({ title: 'Assistants IA — DevLeadHunter' })

const toast: UseToastReturn = useToast()
const drawerStack: ReturnType<typeof useDrawerStackStore> = useDrawerStackStore()

const assistants: Ref<AiAssistantSummary[]> = ref([])
const requests: Ref<AiAssistantRequestItem[]> = ref([])
/** Real requests still waiting for handling (tests excluded), as counted by the API. */
const pendingRequestCount: Ref<number> = ref(0)
const requestFilter: Ref<string> = ref('new')
const requestBusyId: Ref<number | null> = ref(null)
const isLoading: Ref<boolean> = ref(true)
const confirmingId: Ref<number | null> = ref(null)
const regeneratingId: Ref<number | null> = ref(null)
const videoBusyId: Ref<number | null> = ref(null)
const videoPollTimer: Ref<ReturnType<typeof setInterval> | null> = ref(null)
const subscriptionBusyId: Ref<number | null> = ref(null)

/** The assistant being customized (null = the modal is closed). */
const editing: Ref<AiAssistantSummary | null> = ref(null)
const editForm: Ref<AiAssistantEditForm> = ref({
  assistant_name: '',
  business_name: '',
  tone: '',
  accent_color: '',
  languages: [],
  alert_phone: '',
  alert_sms_enabled: true,
  alert_email_enabled: true,
  alert_sms_types: [],
  alert_quiet_start_hour: 22,
  alert_quiet_end_hour: 8,
})
const isSaving: Ref<boolean> = ref(false)

const STATUS_LABELS: Record<string, string> = { active: 'Actif', expired: 'Expiré', delivered: 'Vendu' }

const REQUEST_TYPE_LABELS: Record<AiAssistantRequestType, string> = {
  question: 'Question',
  quote: 'Devis',
  appointment: 'Rendez-vous',
  urgent: 'Urgence',
  other: 'Demande',
}

const REQUEST_TYPE_BADGES: Record<AiAssistantRequestType, string> = {
  question: '',
  quote: 'app-badge--progress',
  appointment: 'app-badge--info',
  urgent: 'app-badge--danger',
  other: '',
}

/** Request types the owner can have texted at once, the ones that cannot wait first. */
const ALERT_TYPE_OPTIONS: { value: AiAssistantRequestType; label: string }[] = [
  { value: 'quote', label: 'Devis' },
  { value: 'appointment', label: 'Rendez-vous' },
  { value: 'urgent', label: 'Urgence' },
  { value: 'question', label: 'Question' },
  { value: 'other', label: 'Autre' },
]

/** Whole hours of the day, for the quiet window. */
const HOUR_OPTIONS: SelectFieldOption<number>[] = Array.from(
  { length: 24 },
  (_: unknown, hour: number): SelectFieldOption<number> => ({ value: hour, label: `${hour} h` }),
)

/** Languages a customer can offer, in the order they matter for the target markets. */
const LANGUAGE_OPTIONS: { code: string; label: string }[] = [
  { code: 'fr', label: 'Français' },
  { code: 'nl', label: 'Nederlands' },
  { code: 'de', label: 'Deutsch' },
  { code: 'en', label: 'English' },
  { code: 'lu', label: 'Lëtzebuergesch' },
  { code: 'it', label: 'Italiano' },
  { code: 'es', label: 'Español' },
]

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
  requests.value.filter((request: AiAssistantRequestItem): boolean => request.status === 'new' && !request.is_test),
)

const requestFilterTabs: ComputedRef<UiFilterTab[]> = computed((): UiFilterTab[] => [
  { key: 'new', label: 'À traiter', count: pendingRequests.value.length },
  { key: 'all', label: 'Toutes', count: requests.value.length },
])

const visibleRequests: ComputedRef<AiAssistantRequestItem[]> = computed((): AiAssistantRequestItem[] =>
  requestFilter.value === 'new' ? pendingRequests.value : requests.value,
)

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
 * Move a request to another status (handled, dropped, or back to new) and refresh its row.
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
 * Format an API timestamp as a short local date and time.
 * @param iso - The API date string (UTC, naive).
 * @returns The localised « jour mois, HH:MM » label.
 */
function formatDateTime(iso: string): string {
  return parseApiDate(iso).toLocaleString('fr-FR', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
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
    toast.success('Script copié — à coller avant </body> du site du client.')
  } catch {
    toast.error('Copie impossible depuis ce navigateur.')
  }
}

/**
 * Soft-delete an assistant after the inline confirmation.
 * @param assistant - The assistant to remove.
 * @returns A promise resolved once removed and the list refreshed.
 */
async function removeAssistant(assistant: AiAssistantSummary): Promise<void> {
  confirmingId.value = null
  try {
    await AiAssistantService.remove(assistant.id)
    assistants.value = assistants.value.filter((item: AiAssistantSummary): boolean => item.id !== assistant.id)
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
    assistants.value = assistants.value.map(
      (item: AiAssistantSummary): AiAssistantSummary => (item.id === updated.id ? updated : item),
    )
    toast.success('Assistant régénéré depuis les dernières données du prospect.')
  } catch {
    toast.error('Régénération impossible pour le moment.')
  } finally {
    regeneratingId.value = null
  }
}

/** Whether any assistant is mid-generation, which keeps the list polling. */
const hasGeneratingVideo: ComputedRef<boolean> = computed((): boolean =>
  assistants.value.some(
    (item: AiAssistantSummary): boolean => item.video_status === 'pending' || item.video_status === 'generating',
  ),
)

/** Poll the list every few seconds while a video is generating, then stop. */
function startVideoPolling(): void {
  if (videoPollTimer.value !== null) return
  videoPollTimer.value = setInterval((): void => {
    if (!hasGeneratingVideo.value) {
      stopVideoPolling()
      return
    }
    void loadData()
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
      toast.success('Vidéo générée sur votre ordinateur ✓')
      return
    }
    if (build.status === 'failed') {
      toast.info('Génération locale indisponible — bascule sur le serveur…')
    }

    // 'unavailable' (web build, no sidecar) or 'failed' → server-side generation (memory-guarded).
    const updated: AiAssistantSummary = await AiAssistantService.generateVideo(assistant.id)
    patchAssistant(updated)
    toast.success('Génération de la vidéo lancée.')
    startVideoPolling()
  } catch {
    toast.error("Vidéo impossible — enregistrez d'abord votre clip webcam « assistant » dans les paramètres.")
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
      `Lien d'abonnement ${interval === 'year' ? 'annuel' : 'mensuel'} copié — envoyez-le au client, il reste valable.`,
    )
  } catch {
    toast.error('Lien indisponible pour cet assistant.')
  } finally {
    subscriptionBusyId.value = null
  }
}

/**
 * Human label for an assistant's active subscription (e.g. « 29 €/mois »).
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
 * @returns « Actif », « Expiré », « Vendu », or the raw status for the transient ones.
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
 * Open the customization modal, prefilled from the assistant.
 * @param assistant - The assistant to edit.
 */
function openEdit(assistant: AiAssistantSummary): void {
  editing.value = assistant
  editForm.value = {
    assistant_name: assistant.assistant_name,
    business_name: assistant.business_name,
    tone: assistant.tone ?? '',
    accent_color: assistant.accent_color ?? '',
    languages: [...assistant.languages],
    alert_phone: assistant.alerts.phone ?? '',
    alert_sms_enabled: assistant.alerts.sms_enabled,
    alert_email_enabled: assistant.alerts.email_enabled,
    alert_sms_types: [...assistant.alerts.sms_types],
    alert_quiet_start_hour: assistant.alerts.quiet_start_hour,
    alert_quiet_end_hour: assistant.alerts.quiet_end_hour,
  }
}

/** Close the customization modal without saving. */
function closeEdit(): void {
  editing.value = null
}

/**
 * Toggle a language in the edit form.
 * @param code - The language code to toggle.
 */
function toggleLanguage(code: string): void {
  const languages: string[] = editForm.value.languages
  editForm.value.languages = languages.includes(code)
    ? languages.filter((item: string): boolean => item !== code)
    : [...languages, code]
}

/**
 * Toggle a request type in the SMS alert rules of the edit form.
 * @param type - The request type to toggle.
 */
function toggleAlertType(type: AiAssistantRequestType): void {
  const types: AiAssistantRequestType[] = editForm.value.alert_sms_types
  editForm.value.alert_sms_types = types.includes(type)
    ? types.filter((item: AiAssistantRequestType): boolean => item !== type)
    : [...types, type]
}

/**
 * The alert settings the form changed, so an untouched setting keeps following the API default.
 * @param alerts - The assistant's current alert settings.
 * @param form - The edit form.
 * @returns Only the alert fields that differ from the current settings.
 */
function changedAlertFields(alerts: AiAssistantAlertSettings, form: AiAssistantEditForm): AiAssistantUpdatePayload {
  const changes: AiAssistantUpdatePayload = {}
  if (form.alert_phone.trim() !== (alerts.phone ?? '')) changes.alert_phone = form.alert_phone.trim()
  if (form.alert_sms_enabled !== alerts.sms_enabled) changes.alert_sms_enabled = form.alert_sms_enabled
  if (form.alert_email_enabled !== alerts.email_enabled) changes.alert_email_enabled = form.alert_email_enabled
  const sameTypes: boolean =
    form.alert_sms_types.length === alerts.sms_types.length &&
    form.alert_sms_types.every((type: AiAssistantRequestType): boolean => alerts.sms_types.includes(type))
  if (!sameTypes) changes.alert_sms_types = form.alert_sms_types
  if (form.alert_quiet_start_hour !== alerts.quiet_start_hour) {
    changes.alert_quiet_start_hour = form.alert_quiet_start_hour
  }
  if (form.alert_quiet_end_hour !== alerts.quiet_end_hour) changes.alert_quiet_end_hour = form.alert_quiet_end_hour
  return changes
}

/**
 * Persist the customization and refresh the edited card.
 * @returns A promise resolved once saved.
 */
async function saveEdit(): Promise<void> {
  const target: AiAssistantSummary | null = editing.value
  if (!target || isSaving.value) return
  isSaving.value = true
  try {
    const payload: AiAssistantUpdatePayload = {
      assistant_name: editForm.value.assistant_name,
      business_name: editForm.value.business_name,
      tone: editForm.value.tone,
      accent_color: editForm.value.accent_color,
      languages: editForm.value.languages,
      ...changedAlertFields(target.alerts, editForm.value),
    }
    const updated: AiAssistantSummary = await AiAssistantService.update(target.id, payload)
    assistants.value = assistants.value.map(
      (item: AiAssistantSummary): AiAssistantSummary => (item.id === updated.id ? updated : item),
    )
    editing.value = null
    toast.success('Assistant personnalisé.')
  } catch (error: unknown) {
    // The API explains an alert number it cannot text; anything else stays generic.
    const detail: string = error instanceof Error ? error.message : ''
    toast.error(detail.startsWith("Numéro d'alerte") ? detail : 'Enregistrement impossible pour le moment.')
  } finally {
    isSaving.value = false
  }
}

/**
 * Load the assistants and the requests their visitors left.
 * @returns A promise resolved once both are loaded.
 */
async function loadData(): Promise<void> {
  isLoading.value = true
  try {
    const [assistantList, requestList]: [AiAssistantListResponse, AiAssistantRequestsResponse] = await Promise.all([
      AiAssistantService.list(),
      AiAssistantService.listRequests(),
    ])
    assistants.value = assistantList.assistants
    requests.value = requestList.requests
    pendingRequestCount.value = requestList.pending_count
  } catch {
    toast.error('Chargement des assistants impossible.')
  } finally {
    isLoading.value = false
  }
}

onMounted(async (): Promise<void> => {
  await loadData()
  if (hasGeneratingVideo.value) startVideoPolling()
})

onUnmounted((): void => {
  stopVideoPolling()
})
</script>
