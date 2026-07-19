<template>
  <div class="space-y-6">
    <!-- Active sending method ------------------------------------------------ -->
    <div class="card">
      <h2 class="text-sm font-semibold text-[var(--app-ink)]">Méthode d'envoi active</h2>
      <p class="text-muted mt-1 mb-4 text-xs">
        Le canal par lequel partent vos emails de prospection. Configurez celui de votre choix ci-dessous, puis
        sélectionnez-le ici.
      </p>

      <div class="inline-flex rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-0.5">
        <button
          type="button"
          :class="providerTabClass('resend')"
          :disabled="isSwitching"
          @click="switchProvider('resend')"
        >
          <UIcon name="i-lucide-mail-open" class="h-4 w-4" />
          <span>Domaine (Resend)</span>
          <UIcon v-if="activeProvider === 'resend'" name="i-lucide-check" class="h-3.5 w-3.5" />
        </button>
        <button
          type="button"
          :class="providerTabClass('gmail')"
          :disabled="isSwitching"
          @click="switchProvider('gmail')"
        >
          <i class="fa-brands fa-google"></i>
          <span>Gmail</span>
          <UIcon v-if="activeProvider === 'gmail'" name="i-lucide-check" class="h-3.5 w-3.5" />
        </button>
      </div>

      <p v-if="activeSummary" class="text-muted mt-3 text-xs">{{ activeSummary }}</p>
    </div>

    <!-- Resend (custom domain) ---------------------------------------------- -->
    <div class="card">
      <div class="mb-4 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <UIcon name="i-lucide-globe" class="h-4 w-4 text-[var(--app-ink)]" />
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Envoi depuis votre domaine (Resend)</h2>
        </div>
        <span
          :class="['app-badge font-semibold', identity?.resend_configured ? 'app-badge--success' : 'app-badge--danger']"
        >
          <UIcon :name="identity?.resend_configured ? 'i-lucide-check' : 'i-lucide-x'" class="h-3.5 w-3.5" />
          {{ identity?.resend_configured ? 'Configuré' : 'Non configuré' }}
        </span>
      </div>

      <p class="text-muted mb-5 text-xs">
        Envoyez depuis <strong class="text-[var(--app-ink)]">votre propre adresse</strong> (ex :
        contact@votredomaine.fr) via Resend. La clé API et le secret webhook sont chiffrés avant stockage.
      </p>

      <form class="space-y-4" @submit.prevent="saveResend">
        <!-- Clé API -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">
            Clé API Resend
            <span class="text-[var(--app-red)]">*</span>
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
              @click="showApiKey = !showApiKey"
            >
              <UIcon :name="showApiKey ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-3.5 w-3.5" />
            </button>
          </div>
          <p class="text-muted mt-1 text-xs">
            Créer une clé sur
            <a href="https://resend.com/api-keys" target="_blank" class="text-[var(--app-accent-ink)] hover:underline">
              resend.com/api-keys
            </a>
          </p>
          <div
            class="mt-2 flex items-start gap-2 rounded-lg border border-[var(--app-accent)]/30 bg-[var(--app-accent-soft)] px-3 py-2"
          >
            <UIcon name="i-lucide-triangle-alert" class="mt-0.5 h-3.5 w-3.5 text-[var(--app-accent)]" />
            <p class="text-xs text-[var(--app-accent)]">
              Utilisez une clé <strong>Full Access</strong> — une clé restreinte "Sending access" ne permettra pas la
              synchronisation des statuts (ouvertures, clics, bounces) depuis la page Emails.
            </p>
          </div>
        </div>

        <!-- Secret webhook -->
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
              @click="showWebhookSecret = !showWebhookSecret"
            >
              <UIcon :name="showWebhookSecret ? 'i-lucide-eye-off' : 'i-lucide-eye'" class="h-3.5 w-3.5" />
            </button>
          </div>
          <p class="text-muted mt-1 text-xs">Trouvable dans Resend → Settings → Webhooks après création du webhook.</p>
        </div>

        <!-- Email d'envoi -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">
            Email d'envoi
            <span class="text-[var(--app-red)]">*</span>
          </label>
          <input
            v-model="resendForm.from_email"
            type="email"
            required
            class="input-field"
            placeholder="contact@votredomaine.fr"
          />
          <p class="text-muted mt-1 text-xs">Doit être un domaine vérifié sur Resend.</p>
        </div>

        <!-- Nom d'envoi -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Nom d'envoi</label>
          <input v-model="resendForm.from_name" type="text" class="input-field" placeholder="Léo" />
          <p class="text-muted mt-1 text-xs">Nom affiché dans la boîte de réception du destinataire.</p>
        </div>

        <div class="pt-1">
          <button
            type="submit"
            :disabled="isSavingResend"
            class="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <UIcon v-if="isSavingResend" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ isSavingResend ? 'Enregistrement…' : 'Enregistrer la configuration Resend' }}
          </button>
        </div>
      </form>

      <!-- Aide webhook -->
      <div class="mt-4 rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-4">
        <h3 class="mb-2 text-xs font-semibold text-[var(--app-ink)]">
          <UIcon name="i-lucide-info" class="mr-1.5 h-4 w-4 text-[var(--app-accent-ink)]" />
          Configuration du webhook
        </h3>
        <p class="text-muted text-xs leading-relaxed">
          Pour le tracking temps réel (ouvertures, clics, bounces), configurez le webhook dans Resend → Settings →
          Webhooks avec l'URL :
        </p>
        <code class="mt-2 block rounded bg-[var(--app-surface)] px-3 py-2 text-xs text-[var(--app-green)]">
          POST https://votre-api.com/api/v1/webhooks/resend
        </code>
        <p class="text-muted mt-2 text-xs">
          Events :
          <span class="text-[var(--app-ink)]"
            >email.sent · email.delivered · email.opened · email.clicked · email.bounced · email.complained</span
          >
        </p>
      </div>
    </div>

    <!-- Gmail --------------------------------------------------------------- -->
    <div class="card">
      <div class="mb-4 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <i class="fa-brands fa-google text-[var(--app-ink)]"></i>
          <h2 class="text-sm font-semibold text-[var(--app-ink)]">Envoi via Gmail</h2>
        </div>
        <span :class="['app-badge font-semibold', identity?.gmail_configured ? 'app-badge--success' : '']">
          <UIcon :name="identity?.gmail_configured ? 'i-lucide-check' : 'i-lucide-minus'" class="h-3.5 w-3.5" />
          {{ identity?.gmail_configured ? 'Connecté' : 'Non connecté' }}
        </span>
      </div>

      <p class="text-muted mb-4 text-xs">
        Pas de domaine ? Envoyez directement depuis votre boîte <strong class="text-[var(--app-ink)]">Gmail</strong>. Un
        clic suffit — aucune configuration DNS.
      </p>

      <!-- Connected accounts -->
      <div v-if="gmailAccounts.length > 0" class="mb-4 space-y-2">
        <div
          v-for="account in gmailAccounts"
          :key="account.id"
          class="flex items-center justify-between rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] px-3 py-2.5"
        >
          <div class="flex items-center gap-2.5">
            <i class="fa-brands fa-google text-[var(--app-ink-soft)]"></i>
            <div>
              <p class="text-sm font-medium text-[var(--app-ink)]">{{ account.email }}</p>
              <p class="text-muted text-xs">{{ account.name }}</p>
            </div>
          </div>
          <button class="btn-danger text-xs" title="Déconnecter ce compte Gmail" @click="deleteGmailAccount(account)">
            <UIcon name="i-lucide-trash-2" class="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <button class="btn-secondary" @click="connectGmail">
        <i class="fa-brands fa-google"></i>
        <span>{{ gmailAccounts.length > 0 ? 'Connecter un autre compte' : 'Connecter Gmail' }}</span>
      </button>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { EmailAccount } from '~/types'
import type { ResendConfigResponse, SendingIdentityResponse, SendingProvider } from '~/services/settingsService'
import { ref, computed, onMounted } from 'vue'
import { settingsService } from '~/services/settingsService'
import { getEmailAccounts, getGmailAuthUrl, deleteEmailAccount } from '~/services/emailAccountsService'
import { useToast } from '~/composables/useToast'

// ─── Composables ────────────────────────────────────────────────────────────

const toast = useToast()
const route = useRoute()
const router = useRouter()

// ─── State ──────────────────────────────────────────────────────────────────

const identity: Ref<SendingIdentityResponse | null> = ref<SendingIdentityResponse | null>(null)
const resendConfig: Ref<ResendConfigResponse | null> = ref<ResendConfigResponse | null>(null)
const gmailAccounts: Ref<EmailAccount[]> = ref<EmailAccount[]>([])

const isSwitching: Ref<boolean> = ref<boolean>(false)
const isSavingResend: Ref<boolean> = ref<boolean>(false)
const showApiKey: Ref<boolean> = ref<boolean>(false)
const showWebhookSecret: Ref<boolean> = ref<boolean>(false)

const resendForm: Ref<{ api_key: string; webhook_secret: string; from_email: string; from_name: string }> = ref({
  api_key: '',
  webhook_secret: '',
  from_email: '',
  from_name: '',
})

// ─── Computed ───────────────────────────────────────────────────────────────

/** The currently active sending provider (defaults to Resend before load). */
const activeProvider: ComputedRef<SendingProvider> = computed(
  (): SendingProvider => identity.value?.provider ?? 'resend',
)

/** Human sentence describing what the active method sends from. */
const activeSummary: ComputedRef<string> = computed((): string => {
  if (!identity.value) return ''
  if (identity.value.provider === 'gmail') {
    return identity.value.gmail_email
      ? `Vos emails partent depuis ${identity.value.gmail_email} (Gmail).`
      : 'Gmail est sélectionné mais aucun compte n’est connecté.'
  }
  return identity.value.resend_from_email
    ? `Vos emails partent depuis ${identity.value.resend_from_email} (Resend).`
    : 'Resend est sélectionné mais n’est pas encore configuré.'
})

// ─── Methods ────────────────────────────────────────────────────────────────

/**
 * Classes of a provider-selection tab for a given provider.
 * @param provider - The provider this tab activates.
 * @returns Tailwind classes reflecting the active state.
 */
function providerTabClass(provider: SendingProvider): string {
  const base =
    'flex cursor-pointer items-center gap-2 rounded-md px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-60'
  return activeProvider.value === provider
    ? `${base} bg-[var(--app-ink)] text-[var(--app-surface)]`
    : `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Load the sending identity, Resend config and connected Gmail accounts.
 * @returns A promise that resolves once all data is loaded.
 */
async function loadAll(): Promise<void> {
  try {
    const [identityData, resendData, accounts] = await Promise.all([
      settingsService.getSendingIdentity(),
      settingsService.getResendConfig().catch((): ResendConfigResponse | null => null),
      getEmailAccounts().catch((): EmailAccount[] => []),
    ])
    identity.value = identityData
    resendConfig.value = resendData
    resendForm.value.from_email = resendData?.from_email ?? ''
    resendForm.value.from_name = resendData?.from_name ?? ''
    gmailAccounts.value = accounts.filter((a: EmailAccount): boolean => a.account_type === 'gmail_oauth')
  } catch {
    toast.error('Échec du chargement de la configuration d’envoi')
  }
}

/**
 * Switch the active sending provider (guarded server-side against unusable providers).
 * @param provider - Target provider.
 * @returns A promise that resolves once the switch is attempted.
 */
async function switchProvider(provider: SendingProvider): Promise<void> {
  if (provider === activeProvider.value || isSwitching.value) return
  isSwitching.value = true
  try {
    identity.value = await settingsService.setSendingProvider(provider)
    toast.success(provider === 'gmail' ? 'Envoi via Gmail activé' : 'Envoi via Resend activé')
  } catch (error: unknown) {
    const detail: string | undefined = extractErrorDetail(error)
    toast.error(detail ?? 'Impossible de changer de méthode d’envoi')
  } finally {
    isSwitching.value = false
  }
}

/**
 * Persist the Resend configuration, then refresh the identity readiness flags.
 * @returns A promise that resolves once the save is complete.
 */
async function saveResend(): Promise<void> {
  isSavingResend.value = true
  try {
    resendConfig.value = await settingsService.saveResendConfig({
      api_key: resendForm.value.api_key,
      webhook_secret: resendForm.value.webhook_secret || undefined,
      from_email: resendForm.value.from_email,
      from_name: resendForm.value.from_name || undefined,
    })
    resendForm.value.api_key = ''
    resendForm.value.webhook_secret = ''
    identity.value = await settingsService.getSendingIdentity()
    toast.success('Configuration Resend enregistrée')
  } catch {
    toast.error('Erreur lors de l’enregistrement')
  } finally {
    isSavingResend.value = false
  }
}

/**
 * Start the Gmail OAuth flow — redirects the browser to Google's consent screen.
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
 * Extract a human error detail from an API error, when present.
 * @param error - Unknown error thrown by the HTTP client.
 * @returns The API ``detail`` string, or undefined.
 */
function extractErrorDetail(error: unknown): string | undefined {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response: unknown = (error as { response?: unknown }).response
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data: unknown = (response as { data?: unknown }).data
      if (typeof data === 'object' && data !== null && 'detail' in data) {
        const detail: unknown = (data as { detail?: unknown }).detail
        if (typeof detail === 'string') return detail
      }
    }
  }
  return undefined
}

/**
 * Surface the Gmail OAuth callback outcome (``?gmail=connected|error``) as a toast,
 * then strip the query param so a refresh does not re-toast.
 * @returns A promise that resolves once feedback is handled.
 */
async function handleGmailCallbackFeedback(): Promise<void> {
  const flag: unknown = route.query.gmail
  if (flag !== 'connected' && flag !== 'error') return
  if (flag === 'connected') {
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
