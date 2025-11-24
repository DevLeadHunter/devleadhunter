<template>
  <div>
    <!-- Header -->
    <div class="flex justify-between items-start mb-6">
      <div class="flex-1">
        <div class="flex items-center gap-3 mb-2">
          <button
            @click="router.push('/dashboard/campaigns')"
            class="text-muted hover:text-[#f9f9f9] transition-colors"
          >
            <i class="fa-solid fa-arrow-left"></i>
          </button>
          <h1 class="text-xl font-semibold text-[#f9f9f9]">{{ campaign?.name || 'Campaign' }}</h1>
          <span
            v-if="campaign"
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
        <p v-if="campaign" class="text-sm text-muted">{{ campaign.description }}</p>
      </div>
      
      <div class="flex gap-2">
        <button
          @click="showEditModal = true"
          class="btn-secondary"
        >
          <i class="fa-solid fa-pen mr-1.5"></i>
          Edit
        </button>
        <button
          v-if="campaign && campaign.prospectIds.length > 0"
          @click="router.push(`/dashboard/campaigns/${route.params.id}/send`)"
          class="btn-primary"
        >
          <i class="fa-solid fa-paper-plane mr-1.5"></i>
          Send
        </button>
        <button
          @click="confirmDelete"
          class="btn-danger"
        >
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="campaign" class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-muted mb-1">Total Prospects</p>
            <p class="text-2xl font-semibold text-[#f9f9f9]">{{ campaignProspects.length }}</p>
          </div>
          <div class="w-12 h-12 bg-[#050505] rounded-full flex items-center justify-center">
            <i class="fa-solid fa-users text-xl text-[#f9f9f9]"></i>
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-muted mb-1">Emails Sent</p>
            <p class="text-2xl font-semibold text-[#f9f9f9]">{{ emailsSent }}</p>
          </div>
          <div class="w-12 h-12 bg-[#050505] rounded-full flex items-center justify-center">
            <i class="fa-solid fa-envelope text-xl text-[#3fb950]"></i>
          </div>
        </div>
      </div>
      
      <div class="card">
        <div class="flex items-center justify-between">
          <div>
            <p class="text-xs text-muted mb-1">Created</p>
            <p class="text-sm font-medium text-[#f9f9f9]">{{ formatDate(campaign.createdAt) }}</p>
          </div>
          <div class="w-12 h-12 bg-[#050505] rounded-full flex items-center justify-center">
            <i class="fa-solid fa-calendar text-xl text-[#58a6ff]"></i>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="flex gap-3 mb-6">
      <button
        @click="showAddProspectsModal = true"
        class="btn-secondary"
      >
        <i class="fa-solid fa-user-plus mr-1.5"></i>
        Add Prospects
      </button>
      <button
        v-if="campaignProspects.length > 0"
        @click="router.push(`/dashboard/campaigns/${route.params.id}/send`)"
        class="btn-primary"
      >
        <i class="fa-solid fa-paper-plane mr-1.5"></i>
        Send Emails
      </button>
    </div>

    <!-- Prospects Table -->
    <div class="card">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-base font-semibold text-[#f9f9f9]">Campaign Prospects</h2>
        <span class="text-xs text-muted">{{ campaignProspects.length }} prospects</span>
      </div>
      
      <div v-if="isLoadingProspects" class="animate-pulse space-y-3">
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
        <div class="h-4 bg-[#2a2a2a] rounded w-full"></div>
      </div>
      
      <div v-else-if="campaignProspects.length === 0" class="text-center py-12">
        <i class="fa-solid fa-users text-5xl text-muted mb-3"></i>
        <p class="text-muted text-sm mb-4">No prospects in this campaign yet</p>
        <button
          @click="showAddProspectsModal = true"
          class="btn-secondary"
        >
          Add Prospects
        </button>
      </div>
      
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-[#30363d]">
              <th class="text-left text-xs font-medium text-muted py-2 px-3">Name</th>
              <th class="text-left text-xs font-medium text-muted py-2 px-3">Email</th>
              <th class="text-left text-xs font-medium text-muted py-2 px-3">Phone</th>
              <th class="text-left text-xs font-medium text-muted py-2 px-3">City</th>
              <th class="text-left text-xs font-medium text-muted py-2 px-3">Category</th>
              <th class="text-right text-xs font-medium text-muted py-2 px-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="prospect in campaignProspects"
              :key="prospect.id"
              class="border-b border-[#30363d] hover:bg-[#2a2a2a] transition-colors"
            >
              <td class="py-2 px-3 text-sm text-[#f9f9f9]">{{ prospect.name }}</td>
              <td class="py-2 px-3 text-sm text-muted">{{ prospect.email || '-' }}</td>
              <td class="py-2 px-3 text-sm text-muted">{{ prospect.phone || '-' }}</td>
              <td class="py-2 px-3 text-sm text-muted">{{ prospect.city || '-' }}</td>
              <td class="py-2 px-3 text-sm text-muted">{{ prospect.category }}</td>
              <td class="py-2 px-3 text-right">
                <button
                  @click="removeProspectFromCampaign(prospect.id)"
                  class="text-[#DC4747] hover:text-[#ff6b6b] text-xs transition-colors"
                >
                  <i class="fa-solid fa-times"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Edit Campaign Modal -->
    <div
      v-if="showEditModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
      @click.self="showEditModal = false"
    >
      <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 w-full max-w-md shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Edit Campaign</h2>
        
        <form @submit.prevent="handleUpdateCampaign" class="space-y-3">
          <div>
            <label for="edit-name" class="block text-xs font-medium text-muted mb-1.5">
              Campaign Name
            </label>
            <input
              id="edit-name"
              v-model="editForm.name"
              type="text"
              required
              class="input-field"
            />
          </div>
          
          <div>
            <label for="edit-description" class="block text-xs font-medium text-muted mb-1.5">
              Description
            </label>
            <textarea
              id="edit-description"
              v-model="editForm.description"
              class="input-field"
              rows="3"
            />
          </div>

          <div>
            <label for="edit-status" class="block text-xs font-medium text-muted mb-1.5">
              Status
            </label>
            <select
              id="edit-status"
              v-model="editForm.status"
              class="input-field"
            >
              <option value="draft">Draft</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
            </select>
          </div>
          
          <div class="flex gap-3 pt-2">
            <button
              type="button"
              @click="showEditModal = false"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              type="submit"
              class="btn-primary flex-1"
            >
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Add Prospects Modal -->
    <div
      v-if="showAddProspectsModal"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm"
      @click.self="showAddProspectsModal = false"
    >
      <div class="bg-[#1a1a1a] border border-muted rounded-lg p-6 w-full max-w-2xl shadow-lg">
        <h2 class="text-base font-semibold text-[#f9f9f9] mb-4">Add Prospects to Campaign</h2>
        
        <div v-if="availableProspects.length === 0" class="text-center py-8">
          <i class="fa-solid fa-users text-4xl text-muted mb-3"></i>
          <p class="text-muted text-sm">No available prospects to add</p>
        </div>
        
        <div v-else>
          <div class="max-h-96 overflow-y-auto mb-4">
            <div
              v-for="prospect in availableProspects"
              :key="prospect.id"
              class="flex items-center gap-3 p-3 hover:bg-[#2a2a2a] rounded transition-colors"
            >
              <UiCheckbox
                :id="`prospect-${prospect.id}`"
                :modelValue="selectedProspectIds.includes(prospect.id)"
                @update:modelValue="toggleProspectSelection(prospect.id)"
              />
              <label :for="`prospect-${prospect.id}`" class="flex-1 cursor-pointer">
                <p class="text-sm text-[#f9f9f9]">{{ prospect.name }}</p>
                <p class="text-xs text-muted">{{ prospect.city }} • {{ prospect.category }}</p>
              </label>
            </div>
          </div>
          
          <div class="flex gap-3 pt-2 border-t border-[#30363d]">
            <button
              type="button"
              @click="showAddProspectsModal = false"
              class="btn-secondary flex-1"
            >
              Cancel
            </button>
            <button
              @click="handleAddProspects"
              :disabled="selectedProspectIds.length === 0"
              class="btn-primary flex-1"
            >
              Add {{ selectedProspectIds.length }} Prospect{{ selectedProspectIds.length !== 1 ? 's' : '' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Confirm Delete Modal -->
    <UiConfirmModal
      ref="confirmModal"
      title="Delete Campaign"
      :message="`Are you sure you want to delete the campaign '${campaign?.name}'? This action cannot be undone.`"
      confirm-text="Delete"
      cancel-text="Cancel"
      @confirm="handleDeleteCampaign"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import type { Campaign, Prospect } from '~/types';
import { useCampaignsStore } from '~/stores/campaigns';
import { useProspectsStore } from '~/stores/prospects';
import { useToast } from '~/composables/useToast';

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth'
});

const router = useRouter();
const route = useRoute();
const campaignsStore = useCampaignsStore();
const prospectsStore = useProspectsStore();
const toast = useToast();

const campaign = ref<Campaign | null>(null);
const campaignProspects = ref<Prospect[]>([]);
const isLoadingProspects = ref(false);
const showEditModal = ref(false);
const showAddProspectsModal = ref(false);
const selectedProspectIds = ref<string[]>([]);
const confirmModal = ref<any>(null);
const emailsSent = ref(0);

const editForm = ref({
  name: '',
  description: '',
  status: 'draft' as 'draft' | 'active' | 'completed'
});

// Available prospects (not already in campaign)
const availableProspects = computed(() => {
  return prospectsStore.prospects.filter(
    p => !campaign.value?.prospectIds.includes(p.id)
  );
});

// Format date
const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }).format(date);
};

// Load campaign
const loadCampaign = async () => {
  const campaignId = route.params.id as string;
  campaign.value = campaignsStore.campaigns.find(c => c.id === campaignId) || null;
  
  if (!campaign.value) {
    toast.error('Campaign not found');
    router.push('/dashboard/campaigns');
    return;
  }

  editForm.value = {
    name: campaign.value.name,
    description: campaign.value.description,
    status: campaign.value.status
  };

  await loadCampaignProspects();
};

// Load prospects for this campaign
const loadCampaignProspects = async () => {
  if (!campaign.value) return;
  
  isLoadingProspects.value = true;
  try {
    // Get all prospects from store
    const allProspects = prospectsStore.prospects;
    
    // Filter prospects that are in this campaign
    campaignProspects.value = allProspects.filter(p => 
      campaign.value!.prospectIds.includes(p.id)
    );
  } catch (error) {
    console.error('Failed to load prospects:', error);
  } finally {
    isLoadingProspects.value = false;
  }
};

// Update campaign
const handleUpdateCampaign = async () => {
  if (!campaign.value) return;
  
  try {
    await campaignsStore.updateCampaign(campaign.value.id, {
      name: editForm.value.name,
      description: editForm.value.description,
      status: editForm.value.status
    });
    
    toast.success('Campaign updated');
    showEditModal.value = false;
    await loadCampaign();
  } catch (error) {
    toast.error('Failed to update campaign');
  }
};

// Confirm delete
const confirmDelete = () => {
  confirmModal.value?.open();
};

// Delete campaign
const handleDeleteCampaign = async () => {
  if (!campaign.value) return;
  
  try {
    await campaignsStore.deleteCampaign(campaign.value.id);
    toast.success('Campaign deleted');
    router.push('/dashboard/campaigns');
  } catch (error) {
    toast.error('Failed to delete campaign');
  }
};

// Toggle prospect selection
const toggleProspectSelection = (prospectId: string) => {
  const index = selectedProspectIds.value.indexOf(prospectId);
  if (index > -1) {
    selectedProspectIds.value.splice(index, 1);
  } else {
    selectedProspectIds.value.push(prospectId);
  }
};

// Add prospects to campaign
const handleAddProspects = async () => {
  if (!campaign.value || selectedProspectIds.value.length === 0) return;
  
  try {
    const updatedProspectIds = [
      ...campaign.value.prospectIds,
      ...selectedProspectIds.value
    ];
    
    await campaignsStore.updateCampaign(campaign.value.id, {
      prospectIds: updatedProspectIds
    });
    
    toast.success(`Added ${selectedProspectIds.value.length} prospect(s)`);
    selectedProspectIds.value = [];
    showAddProspectsModal.value = false;
    await loadCampaign();
  } catch (error) {
    toast.error('Failed to add prospects');
  }
};

// Remove prospect from campaign
const removeProspectFromCampaign = async (prospectId: string) => {
  if (!campaign.value) return;
  
  try {
    const updatedProspectIds = campaign.value.prospectIds.filter(id => id !== prospectId);
    
    await campaignsStore.updateCampaign(campaign.value.id, {
      prospectIds: updatedProspectIds
    });
    
    toast.success('Prospect removed');
    await loadCampaign();
  } catch (error) {
    toast.error('Failed to remove prospect');
  }
};

onMounted(async () => {
  await campaignsStore.fetchCampaigns();
  await loadCampaign();
});
</script>






