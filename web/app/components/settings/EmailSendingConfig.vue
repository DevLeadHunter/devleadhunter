<template>
  <!-- No width or centering here: each host page decides its own layout. -->
  <div class="space-y-8">
    <UiTabs v-model="viewProvider" :tabs="TABS">
      <template #icon="{ tab }">
        <UiGoogleLogo v-if="tab.key === 'gmail'" class="h-5 w-5" />
        <UIcon v-else name="i-lucide-globe" class="h-5 w-5" />
      </template>
    </UiTabs>

    <section v-if="viewProvider === 'resend'" class="space-y-6">
      <div class="space-y-3">
        <p class="text-muted text-sm leading-relaxed">
          Envoyez vos emails depuis votre propre adresse (ex :
          <span class="text-[var(--app-ink)]">contact@votredomaine.fr</span>). Idéal pour la crédibilité et la
          délivrabilité à grand volume.
        </p>
        <div v-if="isResendConfigured">
          <span v-if="activeProvider === 'resend'" class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Méthode d'envoi active
          </span>
          <button v-else class="btn-secondary text-xs" @click="activate('resend')">Utiliser cette méthode</button>
        </div>
      </div>

      <div
        v-if="hasReplyCapture"
        class="flex gap-3 rounded-lg border border-[var(--app-green)]/25 bg-[var(--app-green-soft)] px-3 py-3 text-sm"
        role="status"
      >
        <UIcon name="i-lucide-reply" class="mt-0.5 h-4 w-4 shrink-0 text-[var(--app-green)]" />
        <p class="leading-relaxed text-[var(--app-ink)]">
          <span class="font-medium">Réponses détectées automatiquement — rien à configurer.</span>
          Quand un prospect répond à l'un de vos emails, DevLeadHunter le détecte : statut « Répondu », notification, et
          les relances prévues pour ce prospect sont annulées.
        </p>
      </div>

      <UiCollapsibleCard icon="i-lucide-info" title="Comment ça marche" suffix="Côté Resend, 3 étapes">
        <div class="px-4 py-4">
          <ol class="space-y-2.5">
            <li class="flex items-start gap-2.5">
              <span
                class="font-label flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.6rem] font-semibold text-[var(--app-ink)]"
              >
                1
              </span>
              <p class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
                Créez un compte gratuit sur resend.com, ajoutez votre domaine d'envoi (Resend
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Domains) et posez les
                enregistrements DNS demandés chez votre hébergeur pour le vérifier.
              </p>
            </li>
            <li class="flex items-start gap-2.5">
              <span
                class="font-label flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.6rem] font-semibold text-[var(--app-ink)]"
              >
                2
              </span>
              <p class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
                Créez une clé API « Full Access » (Resend
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> API Keys), puis
                collez-la ci-dessous avec votre adresse d'envoi sur ce domaine.
              </p>
            </li>
            <li class="flex items-start gap-2.5">
              <span
                class="font-label flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-[var(--app-surface-2)] text-[0.6rem] font-semibold text-[var(--app-ink)]"
              >
                3
              </span>
              <p class="text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
                Pour le suivi temps réel (ouvertures, clics, bounces) : créez un webhook (Resend
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Webhooks) vers
                <code class="rounded bg-[var(--app-surface-2)] px-1 py-0.5 break-all text-[var(--app-ink)]">{{
                  resendWebhookUrl
                }}</code>
                avec tous les événements « email », puis collez le secret
                <code class="rounded bg-[var(--app-surface-2)] px-1 py-0.5 text-[var(--app-ink)]">whsec_…</code> dans
                les options avancées ci-dessous.
              </p>
            </li>
          </ol>
          <p
            v-if="hasReplyCapture"
            class="mt-3 flex items-center gap-2 border-t border-[var(--app-line-soft)] pt-3 text-[11px] text-[var(--app-ink-soft)]"
          >
            <UIcon name="i-lucide-reply" class="h-3.5 w-3.5 shrink-0 text-[var(--app-green)]" />
            Les réponses des prospects, elles, ne demandent rien : DevLeadHunter les capte automatiquement.
          </p>
        </div>
      </UiCollapsibleCard>

      <form class="space-y-5" @submit.prevent="saveResend">
        <div
          v-if="showWebhookSecretWarning"
          class="flex gap-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-3 text-sm text-amber-900 dark:text-amber-100"
          role="status"
        >
          <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
          <p class="leading-relaxed">
            <span class="font-medium">Suivi temps réel incomplet.</span>
            Sans secret webhook Resend, les ouvertures, clics et bounces ne seront pas mis à jour automatiquement dans
            DevLeadHunter. Ajoutez-le dans les options avancées ci-dessous et créez le webhook dans votre dashboard
            Resend.
          </p>
        </div>

        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">
            Clé API Resend <span class="text-[var(--app-red)]">*</span>
          </label>
          <div class="relative">
            <input
              v-model="resendForm.api_key"
              :type="showApiKey ? 'text' : 'password'"
              required
              class="input-field pr-10"
              placeholder="re_xxxxxxxxxxxxxxxxxxxx"
            />
            <button
              type="button"
              class="text-muted absolute top-1/2 right-3 -translate-y-1/2 transition-colors hover:text-[var(--app-ink)]"
              :aria-label="showApiKey ? 'Masquer la clé' : 'Afficher la clé'"
              @click="showApiKey = !showApiKey"
            >
              <UIcon :name="showApiKey ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-3.5 w-3.5" />
            </button>
          </div>
          <p class="text-muted mt-1.5 text-xs">
            Créez une clé <span class="font-medium text-[var(--app-ink)]">Full Access</span> sur
            <a
              href="https://resend.com/api-keys"
              target="_blank"
              rel="noopener"
              class="font-medium text-[var(--app-blue)] underline underline-offset-2 hover:opacity-80"
            >
              resend.com/api-keys </a
            >.
          </p>
        </div>

        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">
            Adresse d'envoi <span class="text-[var(--app-red)]">*</span>
          </label>
          <input
            v-model="resendForm.from_email"
            type="email"
            required
            class="input-field"
            placeholder="contact@votredomaine.fr"
          />
          <p class="text-muted mt-1.5 text-xs">Doit appartenir à un domaine vérifié sur Resend.</p>
        </div>

        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Nom affiché</label>
          <input v-model="resendForm.from_name" type="text" class="input-field" :placeholder="fromNamePlaceholder" />
        </div>

        <details class="group rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)]">
          <summary
            class="text-muted flex cursor-pointer items-center justify-between px-3 py-2.5 text-xs font-medium select-none hover:text-[var(--app-ink)]"
          >
            <span class="flex items-center gap-2">
              <UIcon name="i-lucide-sliders-horizontal" class="h-3.5 w-3.5" />
              Options avancées (facultatif)
            </span>
            <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5 transition-transform group-open:rotate-180" />
          </summary>
          <div class="space-y-3 border-t border-[var(--app-line)] px-3 py-3">
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">Secret webhook</label>
              <div class="relative">
                <input
                  v-model="resendForm.webhook_secret"
                  :type="showWebhookSecret ? 'text' : 'password'"
                  class="input-field pr-10"
                  placeholder="whsec_xxxxxxxxxxxxxxxxxxxx"
                />
                <button
                  type="button"
                  class="text-muted absolute top-1/2 right-3 -translate-y-1/2 transition-colors hover:text-[var(--app-ink)]"
                  :aria-label="showWebhookSecret ? 'Masquer le secret' : 'Afficher le secret'"
                  @click="showWebhookSecret = !showWebhookSecret"
                >
                  <UIcon :name="showWebhookSecret ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-3.5 w-3.5" />
                </button>
              </div>
              <p class="text-muted mt-1.5 text-xs">
                Nécessaire pour le suivi temps réel (ouvertures, clics, bounces). Webhook à créer dans Resend
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Settings
                <UIcon name="i-lucide-arrow-right" class="inline-block h-3 w-3 align-[-1px]" /> Webhooks vers
                <code class="rounded bg-[var(--app-surface-2)] px-1 py-0.5 text-[var(--app-ink)]">
                  /api/v1/webhooks/resend </code
                >.
              </p>
            </div>
          </div>
        </details>

        <div class="flex flex-col sm:flex-row sm:justify-end">
          <button type="submit" :disabled="isSavingResend" class="btn-primary h-11 disabled:opacity-50 sm:h-9">
            <UIcon v-if="isSavingResend" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ isSavingResend ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
        </div>
      </form>
    </section>

    <section v-else class="space-y-6">
      <div
        v-if="gmailAccounts.length === 0"
        class="flex flex-col items-center gap-4 rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-6 py-12 text-center"
      >
        <UiGoogleLogo class="h-11 w-11" />
        <div class="space-y-1.5">
          <h2 class="text-base font-semibold text-[var(--app-ink)]">Connectez votre boîte Gmail</h2>
          <p class="text-muted mx-auto max-w-sm text-sm leading-relaxed">
            Un seul clic, aucune configuration DNS. Parfait si vous n'avez pas encore de domaine.
          </p>
        </div>
        <button class="btn-primary" @click="connectGmail">
          <UiGoogleLogo class="h-4 w-4" />
          Connecter Gmail
        </button>
      </div>

      <div v-else class="space-y-4">
        <div v-if="activeProvider === 'gmail'">
          <span class="app-badge app-badge--success font-medium">
            <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
            Méthode d'envoi active
          </span>
        </div>
        <button v-else class="btn-secondary text-xs" @click="activate('gmail')">Utiliser Gmail pour l'envoi</button>

        <div
          v-for="account in gmailAccounts"
          :key="account.id"
          class="flex items-center justify-between rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] px-4 py-3"
        >
          <div class="flex items-center gap-3">
            <UiGoogleLogo class="h-6 w-6" />
            <div>
              <p class="text-sm font-medium text-[var(--app-ink)]">{{ account.email }}</p>
              <p class="text-muted text-xs">{{ account.name }}</p>
            </div>
          </div>
          <button class="btn-danger text-xs" title="Déconnecter ce compte" @click="askDeleteGmailAccount(account)">
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          </button>
        </div>

        <button class="text-muted text-xs font-medium hover:text-[var(--app-ink)]" @click="connectGmail">
          + Connecter un autre compte
        </button>
      </div>

      <p v-if="hasReplyCapture" class="text-muted flex gap-2 text-xs leading-relaxed">
        <UIcon name="i-lucide-info" class="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <span>
          Avec Gmail, les réponses des prospects arrivent directement dans votre boîte Gmail. La détection automatique
          des réponses (statut « Répondu », arrêt des relances) est disponible avec l'envoi par domaine personnalisé.
        </span>
      </p>
    </section>

    <UiConfirmModal
      ref="disconnectModalRef"
      title="Déconnecter le compte"
      :message="accountToDisconnect ? `Déconnecter le compte « ${accountToDisconnect.email} » ?` : ''"
      confirm-text="Déconnecter"
      cancel-text="Annuler"
      @confirm="deleteGmailAccount"
    />
  </div>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, Ref } from 'vue'
import type { EmailAccount } from '~/types'
import type { ResendConfigResponse, SendingIdentityResponse, SendingProvider } from '~/services/settingsService'
import type { UiTab } from '~/types/UiTabs'
import { ref, computed, onMounted } from 'vue'
import { SettingsService } from '~/services/settingsService'
import { EmailAccountsService } from '~/services/emailAccountsService'
import { useToast } from '~/composables/useToast'
import { useUserStore } from '~/stores/user'

const toast: UseToastReturn = useToast()
const userStore: ReturnType<typeof useUserStore> = useUserStore()
const route: ReturnType<typeof useRoute> = useRoute()
const router: ReturnType<typeof useRouter> = useRouter()

const TABS: UiTab[] = [
  { key: 'resend', label: 'Domaine personnalisé', hint: 'Votre adresse pro' },
  { key: 'gmail', label: 'Gmail', hint: 'Sans domaine, en un clic' },
]

const identity: Ref<SendingIdentityResponse | null> = ref(null)
const resendConfig: Ref<ResendConfigResponse | null> = ref(null)
const gmailAccounts: Ref<EmailAccount[]> = ref([])
const accountToDisconnect: Ref<EmailAccount | null> = ref(null)
const disconnectModalRef: Ref<{ open: () => void } | null> = ref(null)
const viewProvider: Ref<SendingProvider> = ref('resend')

const isSavingResend: Ref<boolean> = ref(false)
const showApiKey: Ref<boolean> = ref(false)
const showWebhookSecret: Ref<boolean> = ref(false)

const resendForm: Ref<{ api_key: string; webhook_secret: string; from_email: string; from_name: string }> = ref({
  api_key: '',
  webhook_secret: '',
  from_email: '',
  from_name: '',
})

/** The provider currently used to send (defaults to Resend before load). */
const activeProvider: ComputedRef<SendingProvider> = computed(
  (): SendingProvider => identity.value?.provider ?? 'resend',
)

/** Whether the Resend method is ready to send. */
const isResendConfigured: ComputedRef<boolean> = computed((): boolean => Boolean(identity.value?.resend_configured))

/** Whether the user should be warned about missing webhook secret for tracking. */
const showWebhookSecretWarning: ComputedRef<boolean> = computed((): boolean =>
  Boolean(resendConfig.value?.show_webhook_secret_warning),
)

/** Whether platform-wide prospect-reply capture is active (Resend inbound domain). */
const hasReplyCapture: ComputedRef<boolean> = computed((): boolean => Boolean(identity.value?.reply_capture_enabled))

/** Full webhook URL to paste in the Resend dashboard (copy-ready, no relative path to resolve). */
const resendWebhookUrl: ComputedRef<string> = computed(
  (): string => `${useRuntimeConfig().public.apiBase}/api/v1/webhooks/resend`,
)

const fromNamePlaceholder: ComputedRef<string> = computed((): string => {
  const name: string = userStore.user?.name?.trim() ?? ''
  const company: string = userStore.user?.company_name?.trim() ?? ''
  if (name && company) return `Ex : ${name} — ${company}`
  if (name) return `Ex : ${name}`
  return 'Ex : Jean Dupont — Mon Entreprise'
})

/**
 * Whether a given provider is configured and usable.
 * @param provider - Provider to check.
 * @returns True when that provider can send.
 */
function isConfigured(provider: SendingProvider): boolean {
  return provider === 'gmail' ? Boolean(identity.value?.gmail_configured) : Boolean(identity.value?.resend_configured)
}

/**
 * Load sending identity and Gmail accounts; open the active provider tab.
 * @returns A promise resolved once loaded.
 */
async function loadAll(): Promise<void> {
  try {
    const [identityData, accounts]: [SendingIdentityResponse, EmailAccount[]] = await Promise.all([
      SettingsService.getSendingIdentity(),
      EmailAccountsService.getEmailAccounts().catch((): EmailAccount[] => []),
    ])
    identity.value = identityData
    viewProvider.value = identityData.provider
    resendForm.value.from_email = identityData.resend_from_email ?? ''
    gmailAccounts.value = accounts.filter((a: EmailAccount): boolean => a.account_type === 'gmail_oauth')
    // Pre-fill the display name from the existing Resend config, if any.
    const resend: ResendConfigResponse | null = await SettingsService.getResendConfig().catch(() => null)
    resendConfig.value = resend
    resendForm.value.from_name = resend?.from_name ?? ''
  } catch {
    toast.error('Échec du chargement de la configuration d’envoi')
  }
}

/**
 * Make a configured provider the active sending method.
 * @param provider - Provider to activate.
 * @param silent - When true, do not toast on success (used for auto-activation).
 * @returns A promise that resolves once the switch is attempted.
 */
async function activate(provider: SendingProvider, silent: boolean = false): Promise<void> {
  try {
    identity.value = await SettingsService.setSendingProvider(provider)
    if (!silent) {
      toast.success(provider === 'gmail' ? 'Envoi via Gmail activé' : 'Envoi via votre domaine activé')
    }
  } catch {
    if (!silent) toast.error('Impossible d’activer cette méthode')
  }
}

/**
 * Auto-activate the method just configured when no usable method is active yet
 * (keeps onboarding seamless without ever forcing a switch away from a working one).
 * @param justConfigured - The provider that was just set up.
 * @returns A promise that resolves once handled.
 */
async function maybeAutoActivate(justConfigured: SendingProvider): Promise<void> {
  if (activeProvider.value !== justConfigured && !isConfigured(activeProvider.value)) {
    await activate(justConfigured, true)
  }
}

/**
 * Persist the Resend configuration, refresh readiness, then auto-activate if needed.
 * @returns A promise that resolves once the save completes.
 */
async function saveResend(): Promise<void> {
  isSavingResend.value = true
  try {
    await SettingsService.saveResendConfig({
      api_key: resendForm.value.api_key,
      webhook_secret: resendForm.value.webhook_secret || undefined,
      from_email: resendForm.value.from_email,
      from_name: resendForm.value.from_name || undefined,
    })
    resendForm.value.api_key = ''
    resendForm.value.webhook_secret = ''
    resendConfig.value = await SettingsService.getResendConfig()
    identity.value = await SettingsService.getSendingIdentity()
    await maybeAutoActivate('resend')
    toast.success('Configuration enregistrée')
  } catch {
    toast.error('Erreur lors de l’enregistrement')
  } finally {
    isSavingResend.value = false
  }
}

/**
 * Start the Gmail OAuth flow (redirects the browser to Google's consent screen).
 * @returns A promise that resolves once the auth URL is fetched (before redirect).
 */
async function connectGmail(): Promise<void> {
  try {
    const { auth_url }: { auth_url: string; instructions: string } = await EmailAccountsService.getGmailAuthUrl()
    window.location.href = auth_url
  } catch {
    toast.error('Échec de la connexion Gmail')
  }
}

/**
 * Open the confirmation modal for disconnecting a Gmail account.
 * @param account - The Gmail account to remove.
 */
function askDeleteGmailAccount(account: EmailAccount): void {
  accountToDisconnect.value = account
  disconnectModalRef.value?.open()
}

/**
 * Disconnect the Gmail account selected in the confirmation modal.
 * @returns A promise that resolves once the account is deleted.
 */
async function deleteGmailAccount(): Promise<void> {
  const account: EmailAccount | null = accountToDisconnect.value
  if (!account) return
  try {
    await EmailAccountsService.deleteEmailAccount(account.id)
    gmailAccounts.value = gmailAccounts.value.filter((a: EmailAccount): boolean => a.id !== account.id)
    identity.value = await SettingsService.getSendingIdentity()
    toast.success('Compte Gmail déconnecté')
  } catch {
    toast.error('Échec de la déconnexion')
  }
}

/**
 * Surface Gmail OAuth callback (`?gmail=connected|error`), refresh and strip query.
 * @returns A promise resolved once handled.
 */
async function handleGmailCallbackFeedback(): Promise<void> {
  const flag: unknown = route.query.gmail
  if (flag !== 'connected' && flag !== 'error') return
  if (flag === 'connected') {
    viewProvider.value = 'gmail'
    await maybeAutoActivate('gmail')
    toast.success('Compte Gmail connecté')
  } else {
    toast.error('La connexion Gmail a échoué')
  }
  await router.replace({ query: { ...route.query, gmail: undefined } })
}

onMounted(async (): Promise<void> => {
  await loadAll()
  await handleGmailCallbackFeedback()
})
</script>
