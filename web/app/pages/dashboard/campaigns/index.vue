<template>
  <div>
    <div class="mb-4 flex items-center justify-between">
      <h1 class="text-xl font-semibold text-[#f9f9f9]">Campagnes</h1>
      <button class="btn-primary" @click="showCreateModal = true">
        <i class="fa-solid fa-plus mr-1.5"></i>
        <span>Nouvelle campagne</span>
      </button>
    </div>

    <!-- Chargement -->
    <div v-if="campaignsStore.isLoading" class="card">
      <div class="animate-pulse space-y-3">
        <div class="h-4 w-3/4 rounded bg-[#2a2a2a]"></div>
        <div class="h-4 w-full rounded bg-[#2a2a2a]"></div>
      </div>
    </div>

    <!-- Liste des campagnes -->
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
            <p v-if="campaign.description" class="text-muted mb-2 text-sm">
              {{ campaign.description }}
            </p>
            <div class="flex flex-wrap gap-2 text-xs">
              <span class="text-muted">
                <i class="fa-solid fa-users mr-1"></i>
                {{ campaign.prospects_count }} prospect{{ campaign.prospects_count !== 1 ? 's' : '' }}
              </span>
              <span
                :class="[
                  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
                  campaign.status === 'active'
                    ? 'bg-[#2BAD5F]/20 text-[#3fb950]'
                    : campaign.status === 'completed'
                      ? 'bg-[#71A3DB]/20 text-[#58a6ff]'
                      : campaign.status === 'paused'
                        ? 'bg-[#f97316]/20 text-[#f97316]'
                        : 'text-muted bg-[#8b949e]/20',
                ]"
              >
                {{ CAMPAIGN_STATUS_LABELS[campaign.status] ?? campaign.status }}
              </span>
              <span
                v-if="campaign.ab_template_id_b"
                class="inline-flex items-center gap-1 rounded-full bg-[#1f1b40] px-2 py-0.5 text-[10px] font-semibold text-[#a78bfa]"
              >
                <i class="fa-solid fa-flask-vial text-[9px]"></i> A/B
              </span>
            </div>
          </div>
          <i class="fa-solid fa-chevron-right text-muted ml-4 text-xs"></i>
        </div>
      </div>
    </div>

    <!-- État vide -->
    <div v-else class="card py-12 text-center">
      <i class="fa-solid fa-bullhorn text-muted mb-3 text-5xl"></i>
      <p class="text-muted mb-4 text-sm">Aucune campagne pour l'instant</p>
      <button class="btn-secondary" @click="showCreateModal = true">Créer ma première campagne</button>
    </div>

    <!-- Modale de création -->
    <div
      v-if="showCreateModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      @click.self="showCreateModal = false"
    >
      <div class="border-muted w-full max-w-md rounded-lg border bg-[#1a1a1a] p-6 shadow-lg">
        <h2 class="mb-4 text-base font-semibold text-[#f9f9f9]">Nouvelle campagne</h2>

        <form class="space-y-3" @submit.prevent="handleCreateCampaign">
          <div>
            <label for="name" class="text-muted mb-1.5 block text-xs font-medium"> Nom de la campagne </label>
            <input
              id="name"
              v-model="campaignName"
              type="text"
              required
              class="input-field"
              placeholder="Ex : Plombiers Paris"
            />
          </div>

          <div>
            <label for="description" class="text-muted mb-1.5 block text-xs font-medium">
              Description (optionnelle)
            </label>
            <textarea
              id="description"
              v-model="campaignDescription"
              class="input-field"
              rows="3"
              placeholder="Décrivez votre campagne"
            />
          </div>

          <div class="flex gap-3 pt-2">
            <button type="button" class="btn-secondary flex-1" @click="showCreateModal = false">Annuler</button>
            <button type="submit" :disabled="isCreating" class="btn-primary flex-1">
              <i v-if="isCreating" class="fa-solid fa-spinner fa-spin mr-1.5"></i>
              {{ isCreating ? 'Création…' : 'Créer' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, onMounted } from 'vue'
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useCampaignsStore } from '~/stores/campaigns'
import { useToast } from '~/composables/useToast'
import type { CampaignStatus } from '~/services/campaignService'

definePageMeta({
  layout: 'dashboard',
  middleware: 'auth',
})

// ─── Composables ──────────────────────────────────────────────────────────────

const campaignsStore = useCampaignsStore()
const toast = useToast()
const router = useRouter()

// ─── Constants ────────────────────────────────────────────────────────────────

/** French labels for each campaign status value. */
const CAMPAIGN_STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: 'Brouillon',
  active: 'Active',
  completed: 'Terminée',
  paused: 'En pause',
  cancelled: 'Annulée',
}

// ─── State ────────────────────────────────────────────────────────────────────

const showCreateModal: Ref<boolean> = ref(false)
const campaignName: Ref<string> = ref('')
const campaignDescription: Ref<string> = ref('')
const isCreating: Ref<boolean> = ref(false)

// ─── Handlers ─────────────────────────────────────────────────────────────────

/**
 * Submit the create-campaign form, then close the modal on success.
 * @returns A promise that resolves once the campaign has been created.
 */
const handleCreateCampaign = async (): Promise<void> => {
  isCreating.value = true
  try {
    await campaignsStore.createCampaign({
      name: campaignName.value,
      description: campaignDescription.value,
      prospect_ids: [],
    })
    toast.success('Campagne créée avec succès')
    showCreateModal.value = false
    campaignName.value = ''
    campaignDescription.value = ''
  } catch {
    toast.error('Erreur lors de la création de la campagne')
  } finally {
    isCreating.value = false
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted((): void => {
  campaignsStore.fetchCampaigns()
})
</script>
