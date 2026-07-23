<template>
  <div class="mx-auto max-w-2xl space-y-8">
    <!-- Method chooser — one big tab per method, only the selected one is shown below -->
    <UiTabs v-model="viewProvider" :tabs="TABS">
      <template #icon="{ tab }">
        <UiGoogleLogo v-if="tab.key === 'gmail'" class="h-5 w-5" />
        <UIcon v-else name="i-lucide-globe" class="h-5 w-5" />
      </template>
    </UiTabs>

    <!-- ── Domaine personnalisé (Resend) ─────────────────────────────────── -->
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

      <form class="space-y-5" @submit.prevent="saveResend">
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
          <input v-model="resendForm.from_name" type="text" class="input-field" placeholder="Ex : Léo de Dibodev" />
        </div>

        <!-- Advanced (optional) — kept out of the way to stay onboarding-friendly -->
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
                Nécessaire pour le suivi temps réel (ouvertures, clics, bounces). Webhook à créer dans Resend → Settings
                → Webhooks vers
                <code class="rounded bg-[var(--app-surface-2)] px-1 py-0.5 text-[var(--app-ink)]">
                  /api/v1/webhooks/resend </code
                >.
              </p>
            </div>
          </div>
        </details>

        <div class="flex justify-end">
          <button type="submit" :disabled="isSavingResend" class="btn-primary disabled:opacity-50">
            <UIcon v-if="isSavingResend" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ isSavingResend ? 'Enregistrement…' : 'Enregistrer' }}
          </button>
        </div>
      </form>
    </section>

    <!-- ── Gmail ─────────────────────────────────────────────────────────── -->
    <section v-else class="space-y-6">
      <!-- Empty state: friendly one-click connect -->
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

      <!-- Connected -->
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
          <button class="btn-danger text-xs" title="Déconnecter ce compte" @click="deleteGmailAccount(account)">
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          </button>
        </div>

        <button class="text-muted text-xs font-medium hover:text-[var(--app-ink)]" @click="connectGmail">
          + Connecter un autre compte
        </button>
      </div>
    </section>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { EmailAccount } from '~/types'
import type { SendingIdentityResponse, SendingProvider } from '~/services/settingsService'
import type { UiTab } from '~/types/UiTabs'
import { ref, computed, onMounted } from 'vue'
import { settingsService } from '~/services/settingsService'
import { getEmailAccounts, getGmailAuthUrl, deleteEmailAccount } from '~/services/emailAccountsService'
import { useToast } from '~/composables/useToast'

// ─── Composables ────────────────────────────────────────────────────────────

const toast = useToast()
const route = useRoute()
const router = useRouter()

// ─── State ──────────────────────────────────────────────────────────────────

const TABS: UiTab[] = [
  { key: 'resend', label: 'Domaine personnalisé', hint: 'Votre adresse pro' },
  { key: 'gmail', label: 'Gmail', hint: 'Sans domaine, en un clic' },
]

const identity: Ref<SendingIdentityResponse | null> = ref(null)
const gmailAccounts: Ref<EmailAccount[]> = ref([])
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

// ─── Computed ───────────────────────────────────────────────────────────────

/** The provider currently used to send (defaults to Resend before load). */
const activeProvider: ComputedRef<SendingProvider> = computed(
  (): SendingProvider => identity.value?.provider ?? 'resend',
)

/** Whether the Resend method is ready to send. */
const isResendConfigured: ComputedRef<boolean> = computed((): boolean => Boolean(identity.value?.resend_configured))

// ─── Methods ────────────────────────────────────────────────────────────────

/**
 * Whether a given provider is configured and usable.
 * @param provider - Provider to check.
 * @returns True when that provider can send.
 */
function isConfigured(provider: SendingProvider): boolean {
  return provider === 'gmail' ? Boolean(identity.value?.gmail_configured) : Boolean(identity.value?.resend_configured)
}

/**
 * Load the sending identity + connected Gmail accounts and open the tab of the
 * active method.
 * @returns A promise that resolves once loaded.
 */
async function loadAll(): Promise<void> {
  try {
    const [identityData, accounts] = await Promise.all([
      settingsService.getSendingIdentity(),
      getEmailAccounts().catch((): EmailAccount[] => []),
    ])
    identity.value = identityData
    viewProvider.value = identityData.provider
    resendForm.value.from_email = identityData.resend_from_email ?? ''
    gmailAccounts.value = accounts.filter((a: EmailAccount): boolean => a.account_type === 'gmail_oauth')
    // Pre-fill the display name from the existing Resend config, if any.
    const resend = await settingsService.getResendConfig().catch(() => null)
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
async function activate(provider: SendingProvider, silent = false): Promise<void> {
  try {
    identity.value = await settingsService.setSendingProvider(provider)
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
    await settingsService.saveResendConfig({
      api_key: resendForm.value.api_key,
      webhook_secret: resendForm.value.webhook_secret || undefined,
      from_email: resendForm.value.from_email,
      from_name: resendForm.value.from_name || undefined,
    })
    resendForm.value.api_key = ''
    resendForm.value.webhook_secret = ''
    identity.value = await settingsService.getSendingIdentity()
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
    const { auth_url } = await getGmailAuthUrl()
    window.location.href = auth_url
  } catch {
    toast.error('Échec de la connexion Gmail')
  }
}

/**
 * Disconnect a connected Gmail account after confirmation.
 * @param account - The Gmail account to remove.
 * @returns A promise that resolves once the account is deleted.
 */
async function deleteGmailAccount(account: EmailAccount): Promise<void> {
  if (!confirm(`Déconnecter le compte ${account.email} ?`)) return
  try {
    await deleteEmailAccount(account.id)
    gmailAccounts.value = gmailAccounts.value.filter((a: EmailAccount): boolean => a.id !== account.id)
    identity.value = await settingsService.getSendingIdentity()
    toast.success('Compte Gmail déconnecté')
  } catch {
    toast.error('Échec de la déconnexion')
  }
}

/**
 * Surface the Gmail OAuth callback outcome (``?gmail=connected|error``), refresh,
 * auto-activate on first connect, then strip the query param.
 * @returns A promise that resolves once handled.
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

// ─── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async (): Promise<void> => {
  await loadAll()
  await handleGmailCallbackFeedback()
})
</script>
