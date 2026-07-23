import { defineStore } from 'pinia'
import type { ComputedRef, Ref } from 'vue'
import { ref, computed } from 'vue'
import type {
  CampaignCreatePayload,
  CampaignDetailResponse,
  CampaignListResponse,
  CampaignResponse,
  CampaignStats,
  CampaignStatus,
  CampaignUpdatePayload,
} from '~/services/campaignService'
import { CampaignService } from '~/services/campaignService'
/** Pinia store for campaign CRUD and prospect membership. */
// Pinia ne fournit pas de type nommé pour un store : TypeScript l'élide, il est inécrivable.
// eslint-disable-next-line @typescript-eslint/typedef
export const useCampaignsStore = defineStore('campaigns', () => {
  // State
  const campaigns: Ref<CampaignResponse[]> = ref([])
  const currentCampaign: Ref<CampaignDetailResponse | null> = ref(null)
  const currentStats: Ref<CampaignStats | null> = ref(null)
  const isLoading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)

  // Getters
  const campaignsCount: ComputedRef<number> = computed(() => campaigns.value.length)

  const activeCampaigns: ComputedRef<CampaignResponse[]> = computed(() =>
    campaigns.value.filter((campaign: CampaignResponse) => campaign.status === 'active'),
  )

  const completedCampaigns: ComputedRef<CampaignResponse[]> = computed(() =>
    campaigns.value.filter((campaign: CampaignResponse) => campaign.status === 'completed'),
  )

  const draftCampaigns: ComputedRef<CampaignResponse[]> = computed(() =>
    campaigns.value.filter((campaign: CampaignResponse) => campaign.status === 'draft'),
  )

  /**
   * Fetch all campaigns for the user
   * @param [status] - Optional status filter (draft, active, completed)
   * @returns Promise that resolves when fetch is complete
   * @throws If fetch fails
   */
  async function fetchCampaigns(status?: CampaignStatus): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const response: CampaignListResponse = await CampaignService.list(0, 1000, status)
      campaigns.value = response.campaigns
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement des campagnes'
      campaigns.value = []
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch a single campaign by ID
   * @param id - Campaign ID
   * @returns Campaign details
   * @throws If fetch fails
   */
  async function fetchCampaign(id: number): Promise<CampaignDetailResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign: CampaignDetailResponse = await CampaignService.get(id)
      currentCampaign.value = campaign
      return campaign
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement de la campagne'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Fetch campaign statistics
   * @param id - Campaign ID
   * @returns Campaign statistics
   * @throws If fetch fails
   */
  async function fetchCampaignStats(id: number): Promise<CampaignStats> {
    try {
      const stats: CampaignStats = await CampaignService.getStats(id)
      currentStats.value = stats
      return stats
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement des statistiques'
      throw err
    }
  }

  /**
   * Create a new campaign
   * @param data - Campaign data
   * @param data.name - Campaign name
   * @param data.description - Campaign description
   * @param data.status - Campaign status (draft, active, completed)
   * @param data.prospect_ids - Array of prospect IDs to add
   * @returns Created campaign
   * @throws If creation fails
   */
  async function createCampaign(data: CampaignCreatePayload): Promise<CampaignDetailResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign: CampaignDetailResponse = await CampaignService.create(data)

      // Add to campaigns list
      campaigns.value.unshift(campaign)

      return campaign
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec de la création de la campagne'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Update an existing campaign
   * @param id - Campaign ID
   * @param data - Updated campaign data
   * @param [data.name] - Campaign name
   * @param [data.description] - Campaign description
   * @param [data.status] - Campaign status (draft, active, completed)
   * @returns Updated campaign
   * @throws If update fails
   */
  async function updateCampaign(id: number, data: CampaignUpdatePayload): Promise<CampaignResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign: CampaignDetailResponse = await CampaignService.update(id, data)

      // Update in campaigns list
      const index: number = campaigns.value.findIndex((campaign: CampaignResponse) => campaign.id === id)
      if (index !== -1) {
        campaigns.value[index] = campaign
      }

      // Update current campaign if it's the one being updated
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = {
          ...currentCampaign.value,
          ...campaign,
        }
      }

      return campaign
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec de la mise à jour de la campagne'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Delete a campaign
   * @param id - Campaign ID
   * @returns Promise that resolves when deletion is complete
   * @throws If deletion fails
   */
  async function deleteCampaign(id: number): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      await CampaignService.delete(id)

      // Remove from campaigns list
      campaigns.value = campaigns.value.filter((campaign: CampaignResponse) => campaign.id !== id)

      // Clear current campaign if it's the one being deleted
      if (currentCampaign.value?.id === id) {
        currentCampaign.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec de la suppression de la campagne'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Add prospects to campaign
   * @param campaignId - Campaign ID
   * @param prospectIds - Array of prospect IDs to add
   * @returns Promise that resolves when prospects are added
   * @throws If update fails
   */
  async function addProspectsToCampaign(campaignId: number, prospectIds: number[]): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const campaign: CampaignDetailResponse = await CampaignService.addProspects(campaignId, prospectIds)

      // Update current campaign
      currentCampaign.value = campaign

      // Update in campaigns list
      const index: number = campaigns.value.findIndex((campaign: CampaignResponse) => campaign.id === campaignId)
      if (index !== -1) {
        campaigns.value.splice(index, 1, { ...campaign })
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Échec de l'ajout des prospects"
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Remove a prospect from campaign
   * @param campaignId - Campaign ID
   * @param prospectId - Prospect ID to remove
   * @returns Promise that resolves when prospect is removed
   * @throws If update fails
   */
  async function removeProspectFromCampaign(campaignId: number, prospectId: number): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const campaign: CampaignDetailResponse = await CampaignService.removeProspect(campaignId, prospectId)

      // Update current campaign
      currentCampaign.value = campaign

      // Update in campaigns list
      const index: number = campaigns.value.findIndex((campaign: CampaignResponse) => campaign.id === campaignId)
      if (index !== -1) {
        campaigns.value.splice(index, 1, { ...campaign })
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec de la suppression du prospect'
      throw err
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Get campaign by ID from local state
   * @param id - Campaign ID
   * @returns The campaign or undefined if not found
   */
  function getCampaignById(id: number): CampaignResponse | undefined {
    return campaigns.value.find((campaign: CampaignResponse) => campaign.id === id)
  }

  return {
    // State
    campaigns,
    currentCampaign,
    currentStats,
    isLoading,
    error,
    // Getters
    campaignsCount,
    activeCampaigns,
    completedCampaigns,
    draftCampaigns,
    // Actions
    fetchCampaigns,
    fetchCampaign,
    fetchCampaignStats,
    createCampaign,
    updateCampaign,
    deleteCampaign,
    addProspectsToCampaign,
    removeProspectFromCampaign,
    getCampaignById,
  }
})
