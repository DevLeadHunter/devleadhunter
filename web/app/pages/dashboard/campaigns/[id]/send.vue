<template>
  <div>
    <!-- Back button -->
    <button class="text-muted mb-4 flex items-center gap-2 text-sm hover:text-[#f9f9f9]" @click="$router.back()">
      <i class="fa-solid fa-arrow-left"></i>
      <span>Back to campaigns</span>
    </button>

    <!-- Header -->
    <div class="card mb-4">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Send Campaign</h1>
      <p v-if="campaign" class="text-muted mt-2 text-sm">
        {{ campaign.name }} - {{ campaign.prospectIds.length }} prospect(s)
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <!-- Send form -->
    <div v-else class="card">
      <form class="space-y-4" @submit.prevent="handleSendCampaign">
        <!-- Email Account Selection -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium"> Sender Account * </label>
          <select v-model="sendForm.email_account_id" required class="input-field">
            <option value="">Select an account</option>
            <option v-for="account in emailAccounts.filter((a) => a.is_verified)" :key="account.id" :value="account.id">
              {{ account.name }} ({{ account.email }})
              {{ account.is_default ? ' - Default' : '' }}
            </option>
          </select>
          <p v-if="emailAccounts.filter((a) => a.is_verified).length === 0" class="mt-1.5 text-xs text-[#DC4747]">
            No verified account available.
            <NuxtLink to="/dashboard/email-accounts" class="text-[#58a6ff] hover:underline">
              Configure an email account
            </NuxtLink>
          </p>
        </div>

        <!-- Template Selection -->
        <div>
          <label class="text-muted mb-1.5 block text-xs font-medium"> Email Template * </label>
          <select v-model="sendForm.template_id" required class="input-field" @change="loadTemplatePreview">
            <option value="">Select a template</option>
            <option
              v-for="template in emailTemplates.filter((t) => t.is_active)"
              :key="template.id"
              :value="template.id"
            >
              {{ template.name }} - {{ template.subject }}
            </option>
          </select>
          <p v-if="emailTemplates.filter((t) => t.is_active).length === 0" class="mt-1.5 text-xs text-[#DC4747]">
            No active template available.
            <NuxtLink to="/dashboard/email-templates" class="text-[#58a6ff] hover:underline">
              Create a template
            </NuxtLink>
          </p>
        </div>

        <!-- Template Preview -->
        <div v-if="selectedTemplate" class="border-muted rounded border bg-[#050505] p-3">
          <h3 class="mb-2 text-xs font-medium text-[#f9f9f9]">Template Preview</h3>
          <div class="text-muted mb-2 text-xs">
            <span class="font-medium">Subject:</span> {{ selectedTemplate.subject }}
          </div>
          <div
            v-if="selectedTemplate.variables && selectedTemplate.variables.length > 0"
            class="text-muted mb-2 text-xs"
          >
            <span class="font-medium">Variables:</span> {{ selectedTemplate.variables.join(', ') }}
          </div>
          <div class="border-muted rounded border bg-[#1a1a1a] p-2 text-xs">
            <!-- eslint-disable-next-line vue/no-v-html -- Trusted HTML from user's own email template -->
            <div class="line-clamp-4" v-html="selectedTemplate.body_html"></div>
          </div>
        </div>

        <!-- Prospects Summary -->
        <div class="rounded border border-[#71A3DB]/30 bg-[#71A3DB]/10 p-3">
          <h3 class="mb-1 text-xs font-medium text-[#58a6ff]">Sending Summary</h3>
          <p class="text-xs text-[#58a6ff]">{{ campaign?.prospectIds.length || 0 }} email(s) will be sent</p>
          <p class="text-muted mt-1 text-xs">Variables will be automatically replaced for each prospect</p>
        </div>

        <!-- Warning -->
        <div class="rounded border border-[#DC4747]/30 bg-[#DC4747]/10 p-3">
          <p class="text-xs text-[#DC4747]">
            <i class="fa-solid fa-exclamation-triangle mr-1"></i>
            <strong>Warning:</strong> Once sent, emails cannot be canceled. Double-check your template and prospect
            list.
          </p>
        </div>

        <!-- Actions -->
        <div class="flex gap-3 pt-2">
          <button type="button" class="btn-secondary flex-1" @click="$router.back()">Cancel</button>
          <button type="submit" :disabled="isSending || !canSend" class="btn-primary flex-1">
            <i v-if="isSending" class="fa-solid fa-spinner fa-spin mr-1.5"></i>
            <span>{{ isSending ? 'Sending...' : 'Send Campaign' }}</span>
          </button>
        </div>
      </form>
    </div>

    <!-- Sending Progress Modal -->
    <div
      v-if="showProgressModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
    >
      <div class="border-muted mx-4 w-full max-w-md rounded-lg border bg-[#1a1a1a] p-6">
        <h2 class="mb-6 text-center text-base font-semibold text-[#f9f9f9]">Sending in progress...</h2>

        <div class="mb-6">
          <div class="h-3 w-full overflow-hidden rounded-full bg-[#2a2a2a]">
            <div
              class="h-3 rounded-full bg-[#3fb950] transition-all duration-300"
              :style="{ width: `${sendProgress}%` }"
            ></div>
          </div>
          <p class="text-muted mt-2 text-center text-xs">{{ sentCount }} / {{ totalCount }} emails sent</p>
        </div>

        <div v-if="sendResult" class="space-y-2 text-sm">
          <div class="flex justify-between">
            <span class="text-[#3fb950]"><i class="fa-solid fa-check mr-1"></i>Sent:</span>
            <span class="font-medium text-[#f9f9f9]">{{ sendResult.sent_count }}</span>
          </div>
          <div v-if="sendResult.failed_count > 0" class="flex justify-between">
            <span class="text-[#DC4747]"><i class="fa-solid fa-xmark mr-1"></i>Failed:</span>
            <span class="font-medium text-[#f9f9f9]">{{ sendResult.failed_count }}</span>
          </div>
        </div>

        <button v-if="sendResult" class="btn-primary mt-6 w-full" @click="handleCloseSendModal">Close</button>
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
      toast.error('Campaign not found')
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
    toast.error('Failed to load data')
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

  if (!confirm(`Send ${campaign.value.prospectIds.length} emails?`)) {
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
      toast.success(`${result.sent_count} emails sent successfully`)
      if (result.failed_count > 0) {
        toast.warning(`${result.failed_count} emails failed`)
      }
    } else {
      toast.error('Failed to send campaign')
    }
  } catch (error: unknown) {
    toast.error(error.response?.data?.detail || 'Failed to send')
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
