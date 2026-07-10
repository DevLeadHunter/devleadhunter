<template>
  <div>
    <!-- Back button -->
    <button class="text-muted mb-4 flex items-center gap-2 text-sm hover:text-[var(--app-ink)]" @click="$router.back()">
      <UIcon name="i-lucide-arrow-left" class="h-3.5 w-3.5" />
      <span>Retour aux campagnes</span>
    </button>

    <!-- Header -->
    <div class="card mb-4">
      <h1 class="text-xl font-semibold text-[var(--app-ink)]">Envoyer la campagne</h1>
      <p v-if="campaign" class="text-muted mt-2 text-sm">
        {{ campaign.name }} - {{ campaign.prospectIds.length }} prospect(s)
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[var(--app-surface-2)]"></div>
        <div class="h-4 w-full rounded bg-[var(--app-surface-2)]"></div>
      </div>
    </div>

    <!-- Send form -->
    <div v-else class="card">
      <form class="space-y-4" @submit.prevent="handleSendCampaign">
        <!-- Email Account Selection -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium"> Compte expéditeur * </label>
          <select v-model="sendForm.email_account_id" required class="input-field">
            <option value="">Sélectionner un compte</option>
            <option v-for="account in emailAccounts.filter((a) => a.is_verified)" :key="account.id" :value="account.id">
              {{ account.name }} ({{ account.email }})
              {{ account.is_default ? ' - Par défaut' : '' }}
            </option>
          </select>
          <p
            v-if="emailAccounts.filter((a) => a.is_verified).length === 0"
            class="mt-1.5 text-xs text-[var(--app-red)]"
          >
            Aucun compte vérifié disponible.
            <NuxtLink to="/dashboard/email-accounts" class="text-[var(--app-accent-ink)] hover:underline">
              Configurer un compte email
            </NuxtLink>
          </p>
        </div>

        <!-- Template Selection -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium"> Modèle d'email * </label>
          <select v-model="sendForm.template_id" required class="input-field" @change="loadTemplatePreview">
            <option value="">Sélectionner un modèle</option>
            <option
              v-for="template in emailTemplates.filter((t) => t.is_active)"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} - {{ template.subject }}
            </option>
          </select>
          <p v-if="emailTemplates.filter((t) => t.is_active).length === 0" class="mt-1.5 text-xs text-[var(--app-red)]">
            Aucun modèle actif disponible.
            <NuxtLink to="/dashboard/email-templates" class="text-[var(--app-accent-ink)] hover:underline">
              Créer un modèle
            </NuxtLink>
          </p>
        </div>

        <!-- Template Preview -->
        <div v-if="selectedTemplate" class="border-muted rounded border bg-[var(--app-bg)] p-3">
          <h3 class="mb-2 text-xs font-medium text-[var(--app-ink)]">Aperçu du modèle</h3>
          <div class="text-muted mb-2 text-xs">
            <span class="font-medium">Sujet :</span> {{ selectedTemplate.subject }}
          </div>
          <div
            v-if="selectedTemplate.variables && selectedTemplate.variables.length > 0"
            class="text-muted mb-2 text-xs"
          >
            <span class="font-medium">Variables :</span> {{ selectedTemplate.variables.join(', ') }}
          </div>
          <div class="border-muted rounded border bg-[var(--app-surface)] p-2 text-xs">
            <!-- eslint-disable-next-line vue/no-v-html -- Trusted HTML from user's own email template -->
            <div class="line-clamp-4" v-html="selectedTemplate.body_html"></div>
          </div>
        </div>

        <!-- Prospects Summary -->
        <div class="rounded border border-[var(--app-accent-ink)]/30 bg-[var(--app-accent-ink)]/10 p-3">
          <h3 class="mb-1 text-xs font-medium text-[var(--app-accent-ink)]">Résumé de l'envoi</h3>
          <p class="text-xs text-[var(--app-accent-ink)]">
            {{ campaign?.prospectIds.length || 0 }} email(s) seront envoyés
          </p>
          <p class="text-muted mt-1 text-xs">Les variables seront remplacées automatiquement pour chaque prospect</p>
        </div>

        <!-- Warning -->
        <div class="rounded border border-[var(--app-red)]/30 bg-[var(--app-red)]/10 p-3">
          <p class="text-xs text-[var(--app-red)]">
            <UIcon name="i-lucide-triangle-alert" class="mr-1 inline-block h-3.5 w-3.5 align-[-2px]" />
            <strong>Attention :</strong> une fois partis, les emails ne peuvent pas être annulés. Vérifiez votre modèle
            et votre liste de prospects.
          </p>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-2">
          <button type="button" class="btn-secondary flex-1" @click="$router.back()">Annuler</button>
          <button type="submit" :disabled="isSending || !canSend" class="btn-primary flex-1">
            <UIcon v-if="isSending" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            <span>{{ isSending ? 'Envoi…' : 'Envoyer la campagne' }}</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Sending Progress Modal -->
    <div
      v-if="showProgressModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-[var(--app-overlay)] backdrop-blur-sm"
    >
      <div class="border-muted mx-4 w-full max-w-md rounded-lg border bg-[var(--app-surface)] p-6">
        <h2 class="mb-6 text-center text-base font-semibold text-[var(--app-ink)]">Envoi en cours…</h2>

        <div class="mb-6">
          <div class="h-3 w-full overflow-hidden rounded-full bg-[var(--app-surface-2)]">
            <div
              class="h-3 rounded-full bg-[var(--app-green)] transition-all duration-300"
              :style="{ width: `${sendProgress}%` }"
            ></div>
          </div>
          <p class="text-muted mt-2 text-center text-xs">{{ sentCount }} / {{ totalCount }} emails envoyés</p>
        </div>

        <div v-if="sendResult" class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="flex items-center gap-1.5 text-[var(--app-green)]"
              ><UIcon name="i-lucide-check" class="h-3.5 w-3.5" />Envoyés :</span
            >
            <span class="font-medium text-[var(--app-ink)]">{{ sendResult.sent_count }}</span>
          </div>
          <div v-if="sendResult.failed_count > 0" class="flex justify-between">
            <span class="flex items-center gap-1.5 text-[var(--app-red)]"
              ><UIcon name="i-lucide-x" class="h-3.5 w-3.5" />Échecs :</span
            >
            <span class="font-medium text-[var(--app-ink)]">{{ sendResult.failed_count }}</span>
          </div>
        </div>

        <button v-if="sendResult" class="btn-primary mt-6 w-full" @click="handleCloseSendModal">Fermer</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { Campaign, EmailAccount, EmailTemplate } from '~/types'
import { useCampaignsStore } from '~/stores/campaigns'
import { useProspectsStore } from '~/stores/prospects'
import { getEmailAccounts } from '~/services/emailAccountsService'
import { getEmailTemplates } from '~/services/emailTemplatesService'
import { sendCampaignEmails } from '~/services/emailCampaignsService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const router = useRouter()
const route = useRoute()
const toast = useToast()
const campaignsStore = useCampaignsStore()
const prospectsStore = useProspectsStore()

// State
const campaign = ref<Campaign | null>(null)
const emailAccounts = ref<EmailAccount[]>([])
const emailTemplates = ref<EmailTemplate[]>([])
const isLoading = ref(false)
const isSending = ref(false)
const showProgressModal = ref(false)
const sentCount = ref(0)
const totalCount = ref(0)
const sendResult = ref<{ sent_count: number; failed_count: number } | null>(null)

// Form
const sendForm = ref({
  email_account_id: null as number | null,
  template_id: null as number | null,
})

// Computed
const selectedTemplate = computed(() => {
  if (!sendForm.value.template_id) return null
  return emailTemplates.value.find((t) => t.id === sendForm.value.template_id)
})

const canSend = computed(() => {
  return (
    sendForm.value.email_account_id &&
    sendForm.value.template_id &&
    campaign.value &&
    campaign.value.prospectIds.length > 0 &&
    emailAccounts.value.some((a) => a.id === sendForm.value.email_account_id && a.is_verified)
  )
})

const sendProgress = computed(() => {
  if (totalCount.value === 0) return 0
  return Math.round((sentCount.value / totalCount.value) * 100)
})

// Load data
const loadData = async () => {
  try {
    isLoading.value = true

    // Load campaign
    const campaignId = route.params.id as string
    await campaignsStore.fetchCampaigns()
    campaign.value = campaignsStore.getCampaignById(campaignId) || null

    if (!campaign.value) {
      toast.error('Campagne introuvable')
      return
    }

    // Load prospects
    await prospectsStore.searchProspects({ category: 'all', city: '' })

    // Load email accounts
    emailAccounts.value = await getEmailAccounts()

    // Load email templates
    emailTemplates.value = await getEmailTemplates()

    // Pre-select default account if available
    const defaultAccount = emailAccounts.value.find((a) => a.is_default && a.is_verified)
    if (defaultAccount) {
      sendForm.value.email_account_id = defaultAccount.id
    }
  } catch (error) {
    toast.error('Erreur lors du chargement des données')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// Load template preview
const loadTemplatePreview = () => {
  // Template preview is computed automatically
}

// Send campaign
const handleSendCampaign = async () => {
  if (!canSend.value || !campaign.value) return

  if (!confirm(`Envoyer ${campaign.value.prospectIds.length} emails ?`)) {
    return
  }

  try {
    isSending.value = true
    showProgressModal.value = true
    totalCount.value = campaign.value.prospectIds.length
    sentCount.value = 0

    // Build variables for each prospect
    const variablesPerProspect: Record<string, Record<string, string>> = {}

    for (const prospectId of campaign.value.prospectIds) {
      const prospect = prospectsStore.prospects.find((p) => p.id === prospectId)
      if (prospect) {
        variablesPerProspect[prospectId] = {
          name: prospect.name || 'Contact',
          company_name: prospect.name || '',
          email: prospect.email || '',
          phone: prospect.phone || '',
          city: prospect.city || '',
          address: prospect.address || '',
        }
      }
    }

    // Send campaign emails
    const result = await sendCampaignEmails({
      email_account_id: sendForm.value.email_account_id!,
      campaign_id: campaign.value.id,
      template_id: sendForm.value.template_id!,
      prospect_ids: campaign.value.prospectIds,
      variables_per_prospect: variablesPerProspect,
    })

    sentCount.value = result.sent_count
    sendResult.value = result

    if (result.success) {
      toast.success(`${result.sent_count} emails envoyés`)
      if (result.failed_count > 0) {
        toast.warning(`${result.failed_count} emails en échec`)
      }
    } else {
      toast.error("Échec de l'envoi de la campagne")
    }
  } catch (error: unknown) {
    toast.error(error.response?.data?.detail || "Échec de l'envoi")
    console.error(error)
    showProgressModal.value = false
  } finally {
    isSending.value = false
  }
}

// Close send modal
const handleCloseSendModal = () => {
  showProgressModal.value = false
  // Navigate to campaigns list
  router.push('/dashboard/campaigns')
}

onMounted(() => {
  loadData()
})
</script>
