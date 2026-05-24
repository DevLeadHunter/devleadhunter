<template>
  <div>
    <!-- Header -->
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Email Accounts</h1>
      <div class="flex gap-3">
        <button class="btn-secondary" @click="showAddCustomDomainModal = true">
          <i class="fa-solid fa-globe mr-1.5"></i>
          <span>Custom Domain</span>
        </button>
        <button class="btn-primary" @click="handleGmailConnect">
          <i class="fa-brands fa-google mr-1.5"></i>
          <span>Connect Gmail</span>
        </button>
      </div>
    </div>

    <!-- Loading state -->
    <div v-if="isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <!-- Email accounts list -->
    <div v-else-if="emailAccounts && emailAccounts.length > 0" class="space-y-2">
      <div v-for="account in emailAccounts" :key="account.id" class="card transition-colors hover:border-[#f9f9f9]">
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <div class="mb-1 flex items-center gap-2">
              <h3 class="text-base font-semibold text-[#f9f9f9]">{{ account.name }}</h3>
              <span
                v-if="account.is_default"
                class="inline-flex items-center rounded-full bg-[#71A3DB]/20 px-2 py-0.5 text-xs font-medium text-[#58a6ff]"
              >
                Default
              </span>
              <span
                v-if="account.is_verified"
                class="inline-flex items-center rounded-full bg-[#2BAD5F]/20 px-2 py-0.5 text-xs font-medium text-[#3fb950]"
              >
                <i class="fa-solid fa-check mr-1"></i>Verified
              </span>
              <span
                v-else
                class="inline-flex items-center rounded-full bg-[#DC4747]/20 px-2 py-0.5 text-xs font-medium text-[#DC4747]"
              >
                <i class="fa-solid fa-exclamation-triangle mr-1"></i>Not Verified
              </span>
            </div>

            <p class="text-muted mb-2 text-sm">{{ account.email }}</p>

            <div class="text-muted flex items-center gap-4 text-xs">
              <span>
                <i
                  :class="account.account_type === 'custom_domain' ? 'fa-solid fa-globe' : 'fa-brands fa-google'"
                  class="mr-1"
                ></i>
                {{ account.account_type === 'custom_domain' ? 'Custom Domain' : 'Gmail OAuth' }}
              </span>
              <span v-if="account.domain">{{ account.domain }}</span>
            </div>

            <!-- DNS verification status for custom domains -->
            <div
              v-if="account.account_type === 'custom_domain' && !account.is_verified"
              class="mt-3 rounded border border-[#DC4747]/30 bg-[#2a2a2a] p-3"
            >
              <p class="mb-2 text-xs font-medium text-[#f9f9f9]">DNS Configuration Required</p>
              <div class="text-muted space-y-1 text-xs">
                <p>
                  SPF:
                  <span :class="account.spf_verified ? 'text-[#3fb950]' : 'text-[#DC4747]'">
                    {{ account.spf_verified ? '✓ Configured' : '✗ Not configured' }}
                  </span>
                </p>
                <p>
                  DKIM:
                  <span :class="account.dkim_verified ? 'text-[#3fb950]' : 'text-[#DC4747]'">
                    {{ account.dkim_verified ? '✓ Configured' : '✗ Not configured' }}
                  </span>
                </p>
              </div>
              <button class="btn-secondary mt-2 text-xs" @click="handleVerifyDns(account)">Verify Now</button>
            </div>
          </div>

          <!-- Actions -->
          <div class="ml-4 flex gap-2">
            <button
              v-if="!account.is_default"
              class="btn-secondary text-xs"
              title="Set as default"
              @click="handleSetDefault(account)"
            >
              Set Default
            </button>
            <button class="btn-danger text-xs" title="Delete" @click="handleDeleteAccount(account)">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="card py-12 text-center">
      <i class="fa-solid fa-at text-muted mb-3 text-5xl"></i>
      <p class="text-muted mb-4 text-sm">No email accounts configured</p>
      <div class="flex justify-center gap-3">
        <button class="btn-secondary" @click="showAddCustomDomainModal = true">
          <i class="fa-solid fa-globe mr-1.5"></i>
          <span>Custom Domain</span>
        </button>
        <button class="btn-primary" @click="handleGmailConnect">
          <i class="fa-brands fa-google mr-1.5"></i>
          <span>Connect Gmail</span>
        </button>
      </div>
    </div>

    <!-- Add Custom Domain Modal -->
    <div
      v-if="showAddCustomDomainModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      @click.self="showAddCustomDomainModal = false"
    >
      <div class="border-muted mx-4 w-full max-w-lg rounded-lg border bg-[#1a1a1a] p-6">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">Add Custom Domain</h2>

        <form class="space-y-3" @submit.prevent="handleAddCustomDomain">
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Sender Name </label>
            <input
              v-model="customDomainForm.name"
              type="text"
              required
              placeholder="e.g., Jean Dupont"
              class="input-field"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Email Address </label>
            <input
              v-model="customDomainForm.email"
              type="email"
              required
              placeholder="contact@yourdomain.com"
              class="input-field"
              @blur="extractDomainFromEmail"
            />
          </div>

          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium"> Domain </label>
            <input
              v-model="customDomainForm.domain"
              type="text"
              required
              placeholder="yourdomain.com"
              class="input-field"
            />
          </div>

          <UiCheckbox id="is_default" v-model="customDomainForm.is_default" label="Set as default account" />

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showAddCustomDomainModal = false">Cancel</button>
            <button type="submit" :disabled="isSaving" class="btn-primary flex-1">
              {{ isSaving ? 'Adding...' : 'Add Account' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- DNS Instructions Modal -->
    <div
      v-if="showDnsInstructionsModal && dnsInstructions"
      class="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/70 backdrop-blur-sm"
      @click.self="showDnsInstructionsModal = false"
    >
      <div class="border-muted mx-4 my-8 w-full max-w-2xl rounded-lg border bg-[#1a1a1a] p-6">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">DNS Configuration Instructions</h2>

        <div class="border-muted mb-4 overflow-x-auto rounded border bg-[#050505] p-4">
          <pre class="text-muted whitespace-pre-wrap text-xs">{{ dnsInstructions }}</pre>
        </div>

        <button class="btn-primary w-full" @click="showDnsInstructionsModal = false">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { EmailAccount } from '~/types'
import {
  getEmailAccounts,
  createCustomDomainAccount,
  getGmailAuthUrl,
  verifyDnsRecords,
  updateEmailAccount,
  deleteEmailAccount,
} from '~/services/emailAccountsService'
import { useToast } from '~/composables/useToast'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

const toast = useToast()

// State
const emailAccounts = ref<EmailAccount[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const showAddCustomDomainModal = ref(false)
const showDnsInstructionsModal = ref(false)
const dnsInstructions = ref<string | null>(null)

// Form data
const customDomainForm = ref({
  name: '',
  email: '',
  domain: '',
  is_default: false,
})

// Extract domain from email on blur
const extractDomainFromEmail = () => {
  if (customDomainForm.value.email && !customDomainForm.value.domain) {
    const emailParts = customDomainForm.value.email.split('@')
    if (emailParts.length === 2 && emailParts[1]) {
      customDomainForm.value.domain = emailParts[1]
    }
  }
}

// Load email accounts
const loadEmailAccounts = async () => {
  try {
    isLoading.value = true
    emailAccounts.value = await getEmailAccounts()
  } catch (error) {
    toast.error('Échec du chargement des comptes email')
    console.error(error)
  } finally {
    isLoading.value = false
  }
}

// Add custom domain account
const handleAddCustomDomain = async () => {
  try {
    isSaving.value = true
    const newAccount = await createCustomDomainAccount(customDomainForm.value)

    emailAccounts.value.push(newAccount)
    toast.success('Compte ajouté avec succès')

    showAddCustomDomainModal.value = false
    customDomainForm.value = { name: '', email: '', domain: '', is_default: false }

    // Show DNS instructions
    const verification = await verifyDnsRecords(newAccount.id)
    dnsInstructions.value = verification.instructions
    showDnsInstructionsModal.value = true
  } catch (error: unknown) {
    toast.error(error.response?.data?.detail || "Échec de l'ajout du compte")
    console.error(error)
  } finally {
    isSaving.value = false
  }
}

// Connect Gmail account
const handleGmailConnect = async () => {
  try {
    const { auth_url } = await getGmailAuthUrl()
    // Redirect to Google OAuth
    window.location.href = auth_url
  } catch (error) {
    toast.error('Échec de la connexion Gmail')
    console.error(error)
  }
}

// Verify DNS records
const handleVerifyDns = async (account: EmailAccount) => {
  try {
    const verification = await verifyDnsRecords(account.id)

    // Update local account
    const index = emailAccounts.value.findIndex((a) => a.id === account.id)
    if (index !== -1) {
      emailAccounts.value[index] = {
        ...emailAccounts.value[index],
        spf_verified: verification.spf_verified,
        dkim_verified: verification.dkim_verified,
        is_verified: verification.is_verified,
      }
    }

    if (verification.is_verified) {
      toast.success('DNS vérifié avec succès !')
    } else {
      dnsInstructions.value = verification.instructions
      showDnsInstructionsModal.value = true
      toast.warning('Configuration DNS incomplète')
    }
  } catch (error) {
    toast.error('Échec de la vérification DNS')
    console.error(error)
  }
}

// Set account as default
const handleSetDefault = async (account: EmailAccount) => {
  try {
    await updateEmailAccount(account.id, { is_default: true })

    // Update local state
    emailAccounts.value = emailAccounts.value.map((a) => ({
      ...a,
      is_default: a.id === account.id,
    }))

    toast.success('Compte défini par défaut')
  } catch (error) {
    toast.error('Échec de la mise à jour')
    console.error(error)
  }
}

// Delete account
const handleDeleteAccount = async (account: EmailAccount) => {
  if (!confirm(`Delete account ${account.email}?`)) {
    return
  }

  try {
    await deleteEmailAccount(account.id)
    emailAccounts.value = emailAccounts.value.filter((a) => a.id !== account.id)
    toast.success('Account deleted')
  } catch (error) {
    toast.error('Failed to delete account')
    console.error(error)
  }
}

onMounted(() => {
  loadEmailAccounts()
})
</script>
