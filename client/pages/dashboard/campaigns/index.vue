<template>
  <div>
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-[32px] font-semibold text-[#f9f9f9]">Campaigns</h1>
      <button
        @click="showCreateModal = true"
        class="btn-primary"
      >
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>New Campaign</span>
      </button>
    </div>

    <!-- Campaigns List -->
    <div v-if="campaignsStore.isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 bg-[#2a2a2a] rounded w-3/4"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
      </div>
    </div>

    <div v-else-if="campaignsStore.campaignsCount > 0" class="space-y-2">
      <div
        v-for="campaign in campaignsStore.campaigns"
        :key="campaign.id"
        class="card hover:border-[#f9f9f9] transition-colors cursor-pointer"
        @click="router.push(`/dashboard/campaigns/${campaign.id}`)"
      >
        <div class="flex justify-between items-start">
          <div class="flex-1">
            <h3 class="text-base font-semibold text-[#f9f9f9] mb-1">{{ campaign.name }}</h3>
            <p class="text-sm text-muted mb-2">{{ campaign.description }}</p>
            <div class="flex gap-4 text-xs">
              <span class="text-muted">
                <i class="fa-solid fa-users inline mr-1"></i>
                {{ campaign.prospectIds.length }} prospects
              </span>
              <span
                :class="[
                  'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                  campaign.status === 'active' ? 'bg-[#2BAD5F]/20 text-[#3fb950]' :
                  campaign.status === 'completed' ? 'bg-[#71A3DB]/20 text-[#58a6ff]' :
                  'bg-[#8b949e]/20 text-muted'
                ]"
              >
                {{ campaign.status }}
              </span>
            </div>
          </div>
          <button
            @click.stop="handleSendCampaignEmail(campaign.id)"
            class="btn-secondary ml-4"
          >
            Send Emails
          </button>
        </div>
      </div>
    </div>

    <div v-else class="card text-center py-12">
      <i class="fa-solid fa-envelopes text-5xl text-muted mb-3"></i>
      <p class="text-muted text-sm mb-4">No campaigns yet</p>
      <button
        @click="showCreateModal = true"
        class="btn-secondary"
      >
        Create Your First Campaign
      </button>
    </div>

    <!-- Create Campaign Modal -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
      @click.self="showCreateModal = false"
    >
      <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 w-full max-w-md shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Create Campaign</h2>
        
        <form @submit.prevent="handleCreateCampaign" class="space-y-3">
          <div>
            <label for="name" class="block text-xs font-medium text-muted mb-1.5">
              Campaign Name
            </label>
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
            <label for="description" class="block text-xs font-medium text-muted mb-1.5">
              Description
            </label>
            <textarea
              id="description"
              v-model="campaignDescription"
              class="input-field"
              rows="3"
              placeholder="Describe your campaign"
            />
          </div>
          
          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="showCreateModal = false"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary flex-1"
            >
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue';
import { ref, onMounted } from 'vue';
import { useCampaignsStore } from '~/stores/campaigns';
import { useToast } from '~/composables/useToast';
import { useRouter } from 'vue-router';

/**
 * Dashboard campaigns page
 */
definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

/**
 * Campaigns store
 */
const campaignsStore = useCampaignsStore();

/**
 * Toast composable
 */
const toast = useToast();

/**
 * Router
 */
const router = useRouter();

/**
 * Modal state
 */
const showCreateModal: Ref<boolean> = ref(false);

/**
 * Form state
 */
const campaignName: Ref<string> = ref('');
const campaignDescription: Ref<string> = ref('');

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
      status: 'draft'
    });
    
    toast.success('Campaign created successfully');
    showCreateModal.value = false;
    campaignName.value = '';
    campaignDescription.value = '';
  } catch (error) {
    toast.error('Failed to create campaign');
  }
};

/**
 * Handle send campaign emails
 * @param {string} campaignId - Campaign ID
 * @returns {void}
 */
const handleSendCampaignEmail = (campaignId: string): void => {
  router.push(`/dashboard/campaigns/${campaignId}/send`);
};

/**
 * Lifecycle hook
 */
onMounted(() => {
  campaignsStore.fetchCampaigns();
});
</script>




