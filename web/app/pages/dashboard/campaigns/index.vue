<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Campaigns</h1>
      <button class="btn-primary" @click="showCreateModal = true">
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>New Campaign</span>
      </button>
    </div>

    <!-- Campaigns List -->
    <div v-if="campaignsStore.isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <div v-else-if="campaignsStore.campaignsCount > 0" class="space-y-2">
      <div
        v-for="campaign in campaignsStore.campaigns"
        :key="campaign.id"
        class="card cursor-pointer transition-colors hover:border-[#f9f9f9]"
        @click="router.push(`/dashboard/campaigns/${campaign.id}`)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <h3 class="mb-1 text-base font-semibold text-[#f9f9f9]">{{ campaign.name }}</h3>
            <p class="text-muted mb-2 text-sm">{{ campaign.description }}</p>
            <div class="flex gap-4 text-xs">
              <span class="text-muted">
                <i class="fa-solid fa-users mr-1 inline"></i>
                {{ campaign.prospectIds.length }} prospects
              </span>
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                  campaign.status === 'active'
                    ? 'bg-[#2BAD5F]/20 text-[#3fb950]'
                    : campaign.status === 'completed'
                      ? 'bg-[#71A3DB]/20 text-[#58a6ff]'
                      : 'text-muted bg-[#8b949e]/20',
                ]"
              >
                {{ campaign.status }}
              </span>
            </div>
          </div>
          <button class="btn-secondary ml-4" @click.stop="handleSendCampaignEmail(campaign.id)">Send Emails</button>
        </div>
      </div>
    </div>

    <div v-else class="card py-12 text-center">
      <i class="fa-solid fa-envelopes text-muted mb-3 text-5xl"></i>
      <p class="text-muted mb-4 text-sm">No campaigns yet</p>
      <button class="btn-secondary" @click="showCreateModal = true">Create Your First Campaign</button>
    </div>

    <!-- Create Campaign Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      @click.self="showCreateModal = false"
    >
      <div class="border-muted w-full max-w-md rounded-lg border bg-[#1a1a1a] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">Create Campaign</h2>

        <form class="space-y-3" @submit.prevent="handleCreateCampaign">
          <div>
            <label for="name" class="text-muted mb-1.5 block text-xs font-medium"> Campaign Name </label>
            <input
              id="name"
              v-model="campaignName"
              type="text"
              required
              class="input-field"
              placeholder="e.g., Paris Restaurants"
            />
          </div>

          <div>
            <label for="description" class="text-muted mb-1.5 block text-xs font-medium"> Description </label>
            <textarea
              id="description"
              v-model="campaignDescription"
              class="input-field"
              rows="3"
              placeholder="Describe your campaign"
            />
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showCreateModal = false">Cancel</button>
            <button type="submit" class="btn-primary flex-1">Create</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { ref, onMounted } from 'vue'
import { useCampaignsStore } from '~/stores/campaigns'
import { useToast } from '~/composables/useToast'
import { useRouter } from 'vue-router'

/**
 * Dashboard campaigns page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

/**
 * Campaigns store
 */
const campaignsStore = useCampaignsStore()

/**
 * Toast composable
 */
const toast = useToast()

/**
 * Router
 */
const router = useRouter()

/**
 * Modal state
 */
const showCreateModal: Ref<boolean> = ref(false)

/**
 * Form state
 */
const campaignName: Ref<string> = ref('')
const campaignDescription: Ref<string> = ref('')

/**
 * Handle create campaign
 * @returns {Promise<void>}
 */
const handleCreateCampaign = async (): Promise<void> => {
  try {
    await campaignsStore.createCampaign({
      name: campaignName.value,
      description: campaignDescription.value,
      prospectIds: [],
      status: 'draft',
    })

    toast.success('Campaign created successfully')
    showCreateModal.value = false
    campaignName.value = ''
    campaignDescription.value = ''
  } catch {
    toast.error('Failed to create campaign')
  }
}

/**
 * Handle send campaign emails
 * @param {string} campaignId - Campaign ID
 * @returns {void}
 */
const handleSendCampaignEmail = (campaignId: string): void => {
  router.push(`/dashboard/campaigns/${campaignId}/send`)
}

/**
 * Lifecycle hook
 */
onMounted(() => {
  campaignsStore.fetchCampaigns()
})
</script>
