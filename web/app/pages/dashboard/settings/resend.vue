<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h1 class="text-3xl font-bold text-[var(--app-ink)]">Configuration Resend</h1>
      <p class="text-muted mt-2 text-sm">Configurez votre compte Resend pour envoyer vos emails de prospection.</p>
    </div>

    <!-- Statut actuel -->
    <div class="card">
      <h2 class="mb-4 text-sm font-semibold text-[var(--app-ink)]">Statut actuel</h2>
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-muted text-sm">Clé API</span>
          <span
            :class="[
              'app-badge font-semibold',
              currentConfig?.has_api_key ? 'app-badge--success' : 'app-badge--danger',
            ]"
          >
            <UIcon :name="currentConfig?.has_api_key ? 'i-lucide-check' : 'i-lucide-x'" class="h-3.5 w-3.5" />
            {{ currentConfig?.has_api_key ? 'Configurée' : 'Non configurée' }}
          </span>
        </div>
        <div class="flex items-center justify-between">
          <span class="text-muted text-sm">Secret webhook</span>
          <span :class="['app-badge font-semibold', currentConfig?.has_webhook_secret ? 'app-badge--success' : '']">
            <UIcon
              :name="currentConfig?.has_webhook_secret ? 'i-lucide-check' : 'i-lucide-minus'"
              class="h-3.5 w-3.5"
            />
            {{ currentConfig?.has_webhook_secret ? 'Configuré' : 'Non configuré' }}
          </span>
        </div>
        <div v-if="currentConfig?.from_email" class="flex items-center justify-between">
          <span class="text-muted text-sm">Email d'envoi</span>
          <span class="text-sm text-[var(--app-ink)]">{{ currentConfig.from_email }}</span>
        </div>
        <div v-if="currentConfig?.from_name" class="flex items-center justify-between">
          <span class="text-muted text-sm">Nom d'envoi</span>
          <span class="text-sm text-[var(--app-ink)]">{{ currentConfig.from_name }}</span>
        </div>
      </div>
    </div>

    <!-- Formulaire -->
    <div class="card">
      <h2 class="mb-1 text-sm font-semibold text-[var(--app-ink)]">Mettre à jour la configuration</h2>
      <p class="text-muted mb-5 text-xs">
        La clé API et le secret webhook sont chiffrés avant d'être enregistrés en base de données.
      </p>

      <form class="space-y-4" @submit.prevent="handleSave">
        <!-- Clé API -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">
            Clé API Resend
            <span class="text-[var(--app-red)]">*</span>
          </label>
          <div class="relative">
            <input
              v-model="form.api_key"
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
              v-model="form.webhook_secret"
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
            v-model="form.from_email"
            type="email"
            required
            class="input-field"
            placeholder="leo@mail.dibodev.fr"
          />
          <p class="text-muted mt-1 text-xs">Doit être un domaine vérifié sur Resend.</p>
        </div>

        <!-- Nom d'envoi -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium">Nom d'envoi</label>
          <input v-model="form.from_name" type="text" class="input-field" placeholder="Léo" />
          <p class="text-muted mt-1 text-xs">Nom affiché dans la boîte de réception du destinataire.</p>
        </div>

        <div class="pt-2">
          <button
            type="submit"
            :disabled="isSaving"
            class="btn-primary disabled:cursor-not-allowed disabled:opacity-50"
          >
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            {{ isSaving ? 'Enregistrement…' : 'Enregistrer la configuration' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Aide -->
    <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] p-4">
      <h3 class="mb-2 text-sm font-semibold text-[var(--app-ink)]">
        <UIcon name="i-lucide-info" class="mr-2 h-4 w-4 text-[var(--app-accent-ink)]" />
        Configuration du webhook
      </h3>
      <p class="text-muted text-xs leading-relaxed">
        Pour recevoir le tracking en temps réel (ouvertures, clics, bounces), configurez le webhook dans Resend →
        Settings → Webhooks avec l'URL suivante :
      </p>
      <code class="mt-2 block rounded bg-[var(--app-surface)] px-3 py-2 text-xs text-[var(--app-green)]">
        POST https://votre-api.com/api/v1/webhooks/resend
      </code>
      <p class="text-muted mt-2 text-xs">
        Activez les events :
        <span class="text-[var(--app-ink)]"
          >email.sent · email.delivered · email.opened · email.clicked · email.bounced · email.complained</span
        >
      </p>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import type { Ref } from 'vue'
import { settingsService } from '~/services/settingsService'
import type { ResendConfigResponse } from '~/services/settingsService'
import { useToast } from '~/composables/useToast'

definePageMeta({ layout: 'dashboard', middleware: ['auth'] })

// ─── Composables ──────────────────────────────────────────────────────────────

const toast = useToast()

// ─── State ────────────────────────────────────────────────────────────────────

const currentConfig: Ref<ResendConfigResponse | null> = ref(null)
const isSaving: Ref<boolean> = ref(false)
const showApiKey: Ref<boolean> = ref(false)
const showWebhookSecret: Ref<boolean> = ref(false)

const form: Ref<{ api_key: string; webhook_secret: string; from_email: string; from_name: string }> = ref({
  api_key: '',
  webhook_secret: '',
  from_email: '',
  from_name: '',
})

// ─── Data loading ─────────────────────────────────────────────────────────────

/**
 * Fetch the current Resend configuration and populate the form's non-secret fields.
 * @returns A promise that resolves once the config is loaded.
 */
async function loadConfig(): Promise<void> {
  try {
    currentConfig.value = await settingsService.getResendConfig()
    // Pre-fill non-secret fields so the user doesn't have to retype them
    form.value.from_email = currentConfig.value.from_email ?? ''
    form.value.from_name = currentConfig.value.from_name ?? ''
  } catch {
    // Not yet configured — leave form empty
  }
}

// ─── Handlers ─────────────────────────────────────────────────────────────────

/**
 * Save the Resend configuration to the backend.
 * @returns A promise that resolves once the save is complete.
 */
async function handleSave(): Promise<void> {
  isSaving.value = true
  try {
    currentConfig.value = await settingsService.saveResendConfig({
      api_key: form.value.api_key,
      webhook_secret: form.value.webhook_secret || undefined,
      from_email: form.value.from_email,
      from_name: form.value.from_name || undefined,
    })
    // Clear secrets from the form after saving
    form.value.api_key = ''
    form.value.webhook_secret = ''
    toast.success('Configuration Resend enregistrée')
  } catch {
    toast.error("Erreur lors de l'enregistrement")
  } finally {
    isSaving.value = false
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted((): void => {
  loadConfig()
})
</script>
