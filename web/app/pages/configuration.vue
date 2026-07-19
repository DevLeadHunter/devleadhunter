<template>
  <div>
    <!-- ══════════ Écran d'accueil ══════════════════════════════════════════ -->
    <section v-if="!hasStarted" class="wizard-step">
      <div class="text-center">
        <LandingAsterisk class="text-2xl text-[var(--app-accent)]" />
        <p class="app-label mt-4">Bienvenue{{ firstName ? `, ${firstName}` : '' }}</p>
        <h1 class="mt-2 text-3xl font-bold text-[var(--app-ink)]">Configurons votre espace</h1>
        <p class="text-muted mx-auto mt-3 max-w-md text-sm leading-relaxed">
          Trois réglages et vous pourrez lancer votre première prospection. Comptez deux minutes.
        </p>
      </div>

      <ul class="mx-auto mt-9 max-w-xl space-y-2.5">
        <li
          v-for="item in INTRO_ITEMS"
          :key="item.title"
          class="flex items-start gap-3.5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
        >
          <span
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]"
          >
            <UIcon :name="item.icon" class="h-4 w-4 text-[var(--app-ink)]" />
          </span>
          <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-x-2 gap-y-1">
              <p class="text-sm font-semibold text-[var(--app-ink)]">{{ item.title }}</p>
              <span
                class="rounded-full border px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase"
                :class="
                  item.required
                    ? 'border-[var(--app-line)] bg-[var(--app-surface-2)] text-[var(--app-ink)]'
                    : 'border-transparent px-0 text-[var(--app-ink-soft)]'
                "
              >
                {{ item.required ? 'Requis' : 'Facultatif' }}
              </span>
            </div>
            <p class="text-muted mt-0.5 text-xs leading-relaxed">{{ item.detail }}</p>
          </div>
        </li>
      </ul>

      <div class="mt-9 flex flex-col items-center gap-4">
        <button type="button" class="app-btn-primary px-6" @click="startSetup">
          Commencer
          <UIcon name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
          @click="postponeSetup"
        >
          Je ferai ça plus tard
        </button>
      </div>
    </section>

    <!-- ══════════ Les étapes ═══════════════════════════════════════════════ -->
    <template v-else>
      <UiWizardStepper
        class="mx-auto max-w-2xl"
        :model-value="currentStep"
        :steps="STEPS"
        @update:model-value="goToStep"
      />

      <!-- ── Étape 1 · Méthode d'envoi ───────────────────────────────────── -->
      <div v-if="currentStep === 1" key="step-1" class="wizard-step mt-8 space-y-6">
        <header class="mx-auto max-w-2xl">
          <h1 class="text-2xl font-bold text-[var(--app-ink)]">Comment enverrez-vous vos emails ?</h1>
          <p class="text-muted mt-2 text-sm leading-relaxed">
            Le seul réglage indispensable : sans lui, aucune campagne ne peut partir. Gmail se connecte en un clic ;
            votre propre domaine est plus adapté au volume.
          </p>
        </header>

        <EmailSendingConfig />
      </div>

      <!-- ── Étape 2 · Cadence ───────────────────────────────────────────── -->
      <div v-else-if="currentStep === 2" key="step-2" class="wizard-step mx-auto mt-8 max-w-2xl space-y-6">
        <header>
          <h1 class="text-2xl font-bold text-[var(--app-ink)]">À quel rythme envoyer ?</h1>
          <p class="text-muted mt-2 text-sm leading-relaxed">
            Ces limites protègent votre réputation d'expéditeur : elles étalent les envois au lieu de tout partir d'un
            coup. Les valeurs par défaut conviennent à la plupart des cas.
          </p>
        </header>

        <div class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-5">
          <UiSendPolicyFields v-model="policy" />
        </div>

        <UiCallout variant="info">
          Rien à décider maintenant — ces réglages restent modifiables à tout moment depuis
          <span class="font-medium text-[var(--app-ink)]">Paramètres → Réglages d'envoi</span>.
        </UiCallout>
      </div>

      <!-- ── Étape 3 · Vidéo de prospection ──────────────────────────────── -->
      <div v-else-if="currentStep === 3" key="step-3" class="wizard-step mx-auto mt-8 max-w-2xl space-y-6">
        <!-- La question d'abord : personne ne subit un upload non désiré -->
        <div
          v-if="!wantsVideo"
          class="flex flex-col items-center gap-5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-12 text-center"
        >
          <span
            class="flex h-12 w-12 items-center justify-center rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)]"
          >
            <UIcon name="i-lucide-video" class="h-5 w-5 text-[var(--app-ink)]" />
          </span>
          <div class="space-y-2">
            <h1 class="text-xl font-semibold text-[var(--app-ink)]">Ajouter une vidéo à vos emails ?</h1>
            <p class="text-muted mx-auto max-w-sm text-sm leading-relaxed">
              Vous vous filmez trente secondes, une seule fois. Chaque prospect reçoit ensuite sa vidéo personnalisée,
              avec son site qui défile à l'écran et son prénom en incrustation.
            </p>
          </div>
          <div class="flex flex-wrap items-center justify-center gap-3">
            <button type="button" class="app-btn-primary" @click="wantsVideo = true">
              <UIcon name="i-lucide-video" class="h-3.5 w-3.5" />
              Oui, configurer ma vidéo
            </button>
            <button type="button" class="app-btn-secondary" @click="skipVideo">Non, pas maintenant</button>
          </div>
        </div>

        <template v-else>
          <header>
            <h1 class="text-2xl font-bold text-[var(--app-ink)]">Votre vidéo de prospection</h1>
            <p class="text-muted mt-2 text-sm leading-relaxed">
              Un clip webcam enregistré une seule fois. Chaque site démo génère ensuite sa vidéo personnalisée, prête
              pour vos emails.
            </p>
          </header>

          <PresenterVideoConfig @has-video="hasPresenterVideo = $event" />
        </template>
      </div>

      <!-- ── Étape 4 · C'est prêt ────────────────────────────────────────── -->
      <div v-else key="step-4" class="wizard-step mx-auto mt-8 max-w-2xl space-y-8">
        <div class="text-center">
          <span
            class="inline-flex h-14 w-14 items-center justify-center rounded-full border border-[var(--app-green)] bg-[var(--app-green-soft)]"
          >
            <UiStepCheck class="h-7 w-7 text-[var(--app-green)]" />
          </span>
          <h1 class="mt-5 text-3xl font-bold text-[var(--app-ink)]">Votre espace est prêt</h1>
          <p class="text-muted mx-auto mt-3 max-w-md text-sm leading-relaxed">
            Tout est en place pour trouver vos premiers prospects, leur générer un site et les démarcher.
          </p>
        </div>

        <dl class="space-y-2.5">
          <div
            v-for="entry in recapItems"
            :key="entry.label"
            class="flex items-center gap-3.5 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3.5"
          >
            <UIcon
              :name="entry.done ? 'i-lucide-check' : 'i-lucide-minus'"
              class="h-4 w-4 shrink-0"
              :class="entry.done ? 'text-[var(--app-green)]' : 'text-[var(--app-faint)]'"
            />
            <div class="min-w-0 flex-1">
              <dt class="app-label">{{ entry.label }}</dt>
              <dd class="mt-0.5 text-sm font-medium break-words text-[var(--app-ink)]">{{ entry.value }}</dd>
            </div>
          </div>
        </dl>

        <div class="flex flex-col items-center gap-4">
          <button type="button" class="app-btn-primary px-6" :disabled="isFinishing" @click="finish(true)">
            <UIcon
              :name="isFinishing ? 'i-lucide-loader-circle' : 'i-lucide-rocket'"
              :class="['h-3.5 w-3.5', isFinishing && 'animate-spin']"
            />
            Créer ma première automatisation
          </button>
          <button
            type="button"
            class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
            :disabled="isFinishing"
            @click="finish(false)"
          >
            Aller au tableau de bord
          </button>
        </div>
      </div>

      <!-- ── Navigation (étapes 1 à 3) ───────────────────────────────────── -->
      <div v-if="currentStep < STEPS.length" class="mx-auto max-w-2xl">
        <div
          class="sticky bottom-4 z-10 mt-8 flex items-center justify-between gap-3 rounded-full border border-[var(--app-line)] bg-[var(--app-surface)]/90 px-3 py-2 shadow-lg backdrop-blur"
        >
          <button v-if="currentStep > 1" type="button" class="app-btn-secondary" @click="goToStep(currentStep - 1)">
            <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
            Précédent
          </button>
          <span v-else />

          <div class="flex items-center gap-3">
            <span v-if="blockingHint" class="hidden text-xs text-[var(--app-ink-soft)] sm:block">
              {{ blockingHint }}
            </span>
            <button
              type="button"
              class="app-btn-primary disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="!canContinue || isSavingStep"
              @click="continueStep"
            >
              <UIcon v-if="isSavingStep" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
              Continuer
              <UIcon v-if="!isSavingStep" name="i-lucide-arrow-right" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <p v-if="blockingHint" class="mt-3 text-center text-xs text-[var(--app-ink-soft)] sm:hidden">
          {{ blockingHint }}
        </p>

        <div class="mt-6 text-center">
          <button
            type="button"
            class="cursor-pointer text-xs font-medium text-[var(--app-ink-soft)] underline underline-offset-4 transition-colors hover:text-[var(--app-ink)]"
            @click="postponeSetup"
          >
            Je ferai ça plus tard
          </button>
        </div>
      </div>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { SendPolicy } from '~/types/Automation'
import type { SendingIdentityResponse, SendingProvider } from '~/services/settingsService'
import type { PresenterVideoInfo } from '~/services/presenterVideoService'
import type { UiWizardStep } from '~/types/UiWizardStepper'
import { settingsService } from '~/services/settingsService'
import { getPresenterVideo } from '~/services/presenterVideoService'
import { getSendPolicy, updateSendPolicy } from '~/services/sendPolicyService'
import { useOnboarding } from '~/composables/useOnboarding'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'

/** A row of the « c'est prêt » recap. */
interface RecapItem {
  label: string
  value: string
  done: boolean
}

/** A row of the welcome screen checklist. */
interface IntroItem {
  icon: string
  title: string
  detail: string
  required: boolean
}

definePageMeta({ layout: 'onboarding', middleware: 'auth' })

useSeoMeta({ title: 'Mise en route — DevLeadHunter' })

// ─── Composables ────────────────────────────────────────────────────────────

const toast = useToast()
const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { postpone, clearPostponed } = useOnboarding()

// ─── Constantes ─────────────────────────────────────────────────────────────

/** The wizard steps, in order. */
const STEPS: UiWizardStep[] = [
  { id: 1, label: "Méthode d'envoi", hint: 'Domaine ou Gmail' },
  { id: 2, label: 'Cadence', hint: 'Rythme des envois' },
  { id: 3, label: 'Vidéo', hint: 'Facultatif' },
  { id: 4, label: "C'est prêt", hint: 'Récapitulatif' },
]

/** What the welcome screen promises, in the order it is configured. */
const INTRO_ITEMS: IntroItem[] = [
  {
    icon: 'i-lucide-mail-open',
    title: "Votre méthode d'envoi",
    detail: 'Votre domaine via Resend, ou votre boîte Gmail en un clic.',
    required: true,
  },
  {
    icon: 'i-lucide-sliders-horizontal',
    title: "Votre cadence d'envoi",
    detail: "Combien d'emails par jour, quels jours, à quelles heures.",
    required: false,
  },
  {
    icon: 'i-lucide-video',
    title: 'Votre vidéo de prospection',
    detail: 'Un clip de trente secondes, personnalisé pour chaque prospect.',
    required: false,
  },
]

/** How long between two readiness checks while the sending step is open, in ms. */
const SENDING_POLL_INTERVAL_MS: number = 3000

// ─── État ───────────────────────────────────────────────────────────────────

/** Whether the wizard itself is shown (false = welcome screen). */
const hasStarted: Ref<boolean> = ref<boolean>(false)
/** Current step (1-based). */
const currentStep: Ref<number> = ref<number>(1)
/** Sending identity, refreshed while the first step is open. */
const identity: Ref<SendingIdentityResponse | null> = ref<SendingIdentityResponse | null>(null)
/** The edited sending cadence. */
const policy: Ref<SendPolicy> = ref<SendPolicy>({
  daily_cap: 20,
  days_of_week: [0, 1, 2, 3, 4],
  window_start_hour: 7,
  window_end_hour: 18,
  spacing_minutes: 20,
})
/** Serialized cadence as loaded, to avoid a pointless save. */
const savedPolicy: Ref<string> = ref<string>('')
/** Whether the user opted into configuring a presenter video. */
const wantsVideo: Ref<boolean> = ref<boolean>(false)
/** Whether a presenter clip is actually stored. */
const hasPresenterVideo: Ref<boolean> = ref<boolean>(false)
/** Whether the step transition is waiting on a save. */
const isSavingStep: Ref<boolean> = ref<boolean>(false)
/** Whether the wizard is being marked as completed. */
const isFinishing: Ref<boolean> = ref<boolean>(false)
/** Handle of the sending-readiness poller. */
const sendingPollHandle: Ref<ReturnType<typeof setInterval> | null> = ref<ReturnType<typeof setInterval> | null>(null)

// ─── Computed ───────────────────────────────────────────────────────────────

/** The connected user's first name, for the welcome line. */
const firstName: ComputedRef<string> = computed((): string => (userStore.user?.name ?? '').trim().split(' ')[0] ?? '')

/** Whether the active sending method can actually send. */
const isSendingReady: ComputedRef<boolean> = computed((): boolean => {
  const current: SendingIdentityResponse | null = identity.value
  if (!current) return false
  return current.provider === 'gmail' ? current.gmail_configured : current.resend_configured
})

/** Whether the current step allows moving forward. */
const canContinue: ComputedRef<boolean> = computed((): boolean => {
  if (currentStep.value === 1) return isSendingReady.value
  return true
})

/** Why the « Continuer » button is disabled, when it is. */
const blockingHint: ComputedRef<string> = computed((): string =>
  currentStep.value === 1 && !isSendingReady.value ? "Configurez une méthode d'envoi pour continuer" : '',
)

/** Human summary of the sending method, for the recap. */
const sendingSummary: ComputedRef<string> = computed((): string => {
  const current: SendingIdentityResponse | null = identity.value
  if (!current || !isSendingReady.value) return 'Non configurée'
  if (current.provider === 'gmail') return `Gmail — ${current.gmail_email ?? 'compte connecté'}`
  return `Votre domaine — ${current.resend_from_email ?? 'adresse vérifiée'}`
})

/** The recap rows of the final step. */
const recapItems: ComputedRef<RecapItem[]> = computed((): RecapItem[] => {
  const days: number = policy.value.days_of_week.length
  return [
    { label: "Méthode d'envoi", value: sendingSummary.value, done: isSendingReady.value },
    {
      label: 'Cadence',
      value:
        `${policy.value.daily_cap} emails/jour · ${days} jour${days > 1 ? 's' : ''} par semaine · ` +
        `${String(policy.value.window_start_hour).padStart(2, '0')}h–${String(policy.value.window_end_hour).padStart(2, '0')}h`,
      done: true,
    },
    {
      label: 'Vidéo de prospection',
      value: hasPresenterVideo.value ? 'Clip enregistré' : 'Pas de vidéo — à ajouter quand vous voulez',
      done: hasPresenterVideo.value,
    },
  ]
})

// ─── Méthodes ───────────────────────────────────────────────────────────────

/**
 * Refresh the sending identity and repair a dangling selection: when the active
 * provider is not configured but the other one is (e.g. Gmail was connected from
 * a redirect), switch to the one that can actually send.
 * @returns A promise resolved once refreshed.
 */
async function refreshSendingIdentity(): Promise<void> {
  try {
    const current: SendingIdentityResponse = await settingsService.getSendingIdentity()
    identity.value = current
    const activeIsUsable: boolean = current.provider === 'gmail' ? current.gmail_configured : current.resend_configured
    if (activeIsUsable) return
    const fallback: SendingProvider | null = current.gmail_configured
      ? 'gmail'
      : current.resend_configured
        ? 'resend'
        : null
    if (fallback) identity.value = await settingsService.setSendingProvider(fallback)
  } catch {
    // Non-critical: the step simply stays blocked until the call succeeds.
  }
}

/** Poll the sending identity while the first step is open and not ready yet. */
function syncSendingPoller(): void {
  const shouldPoll: boolean = hasStarted.value && currentStep.value === 1 && !isSendingReady.value
  if (shouldPoll && sendingPollHandle.value === null) {
    sendingPollHandle.value = setInterval((): void => {
      void refreshSendingIdentity()
    }, SENDING_POLL_INTERVAL_MS)
  } else if (!shouldPoll && sendingPollHandle.value !== null) {
    clearInterval(sendingPollHandle.value)
    sendingPollHandle.value = null
  }
}

/**
 * Navigate to a step and scroll back to the top.
 * @param step - Target step (1-based).
 */
function goToStep(step: number): void {
  currentStep.value = step
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
}

/** Leave the welcome screen and start the steps. */
function startSetup(): void {
  hasStarted.value = true
  clearPostponed()
}

/**
 * Persist the cadence when it changed since it was loaded.
 * @returns A promise resolved once saved (or immediately when untouched).
 */
async function persistPolicy(): Promise<void> {
  if (JSON.stringify(policy.value) === savedPolicy.value) return
  if (policy.value.window_end_hour <= policy.value.window_start_hour) {
    throw new Error('La fin de journée doit être après le début')
  }
  if (policy.value.days_of_week.length === 0) {
    throw new Error('Choisissez au moins un jour d’envoi')
  }
  policy.value = await updateSendPolicy(policy.value)
  savedPolicy.value = JSON.stringify(policy.value)
}

/**
 * Validate the current step, persist what it owns, then move forward.
 * @returns A promise resolved once the next step is shown.
 */
async function continueStep(): Promise<void> {
  isSavingStep.value = true
  try {
    if (currentStep.value === 1) {
      await refreshSendingIdentity()
      if (!isSendingReady.value) {
        toast.error("Configurez d'abord une méthode d'envoi")
        return
      }
    }
    if (currentStep.value === 2) await persistPolicy()
    goToStep(currentStep.value + 1)
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Erreur lors de l'enregistrement")
  } finally {
    isSavingStep.value = false
  }
}

/** Skip the video step without configuring anything. */
function skipVideo(): void {
  wantsVideo.value = false
  goToStep(currentStep.value + 1)
}

/**
 * Mark the setup as done, then leave for the app.
 * @param toAutomation - True to land on the automation wizard, false for the dashboard.
 * @returns A promise resolved once redirected.
 */
async function finish(toAutomation: boolean): Promise<void> {
  isFinishing.value = true
  try {
    await userStore.completeOnboarding()
    clearPostponed()
  } catch {
    // Never trap the user on the wizard because of a failed flag update.
  } finally {
    isFinishing.value = false
  }
  await navigateTo(toAutomation ? '/dashboard/automations/new' : '/dashboard')
}

/** Postpone the setup: remember the choice locally and go to the dashboard. */
function postponeSetup(): void {
  postpone()
  void navigateTo('/dashboard')
}

/**
 * Surface the Gmail OAuth outcome forwarded here by the auth middleware, then
 * strip the query parameter.
 * @returns A promise resolved once handled.
 */
async function handleGmailCallbackFeedback(): Promise<void> {
  const flag: unknown = route.query.gmail
  if (flag !== 'connected' && flag !== 'error') return
  hasStarted.value = true
  currentStep.value = 1
  if (flag === 'connected') toast.success('Compte Gmail connecté')
  else toast.error('La connexion Gmail a échoué')
  await router.replace({ query: { ...route.query, gmail: undefined } })
}

// ─── Watchers ───────────────────────────────────────────────────────────────

watch([hasStarted, currentStep, isSendingReady], (): void => {
  syncSendingPoller()
})

// ─── Cycle de vie ───────────────────────────────────────────────────────────

onMounted(async (): Promise<void> => {
  // Re-entering an already finished setup (from Paramètres) skips the welcome.
  if (userStore.user?.onboarding_completed) hasStarted.value = true

  await Promise.all([
    refreshSendingIdentity(),
    getSendPolicy()
      .then((loaded: SendPolicy): void => {
        policy.value = loaded
        savedPolicy.value = JSON.stringify(loaded)
      })
      .catch((): void => {
        savedPolicy.value = ''
      }),
    // An existing clip means the video step opens on its configuration, not on
    // the « do you want one? » question.
    getPresenterVideo()
      .then((video: PresenterVideoInfo): void => {
        hasPresenterVideo.value = video.has_video
        if (video.has_video) wantsVideo.value = true
      })
      .catch((): void => {
        hasPresenterVideo.value = false
      }),
  ])

  await handleGmailCallbackFeedback()
  syncSendingPoller()
})

onBeforeUnmount((): void => {
  if (sendingPollHandle.value !== null) clearInterval(sendingPollHandle.value)
})
</script>

<style scoped>
.wizard-step {
  animation: wizard-step-in 0.3s ease;
}
@keyframes wizard-step-in {
  from {
    opacity: 0;
    transform: translateX(18px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
@media (prefers-reduced-motion: reduce) {
  .wizard-step {
    animation: none;
  }
}
</style>
