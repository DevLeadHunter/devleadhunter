import { defineStore } from 'pinia'
import type { Ref } from 'vue'
import { ref, computed } from 'vue'
import {
  campaignService,
  type CampaignResponse,
  type CampaignDetailResponse,
  type CampaignStats,
} from '~/services/campaignService'

/**
 * Pinia store for campaign management
 * @module stores/campaigns
 */

/**
 * Campaigns store definition
 */
export const useCampaignsStore = defineStore('campaigns', () => {
  // State
  const campaigns: Ref<CampaignResponse[]> = ref([])
  const currentCampaign: Ref<CampaignDetailResponse | null> = ref(null)
  const currentStats: Ref<CampaignStats | null> = ref(null)
  const isLoading: Ref<boolean> = ref(false)
  const error: Ref<string | null> = ref(null)

  // Getters
  const campaignsCount = computed(() => campaigns.value.length)

  const activeCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'active'))

  const completedCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'completed'))

  const draftCampaigns = computed(() => campaigns.value.filter((c) => c.status === 'draft'))

  /**
   * Fetch all campaigns for the user
   * @param {string} [status] - Optional status filter (draft, active, completed)
   * @returns {Promise<void>} Promise that resolves when fetch is complete
   * @throws {Error} If fetch fails
   * @example
   * ```typescript
   * await campaignsStore.fetchCampaigns();
   * ```
   */
  async function fetchCampaigns(status?: string): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const response = await campaignService.list(0, 1000, status)
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
   * @param {number} id - Campaign ID
   * @returns {Promise<CampaignDetailResponse>} Campaign details
   * @throws {Error} If fetch fails
   */
  async function fetchCampaign(id: number): Promise<CampaignDetailResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign = await campaignService.get(id)
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
   * @param {number} id - Campaign ID
   * @returns {Promise<CampaignStats>} Campaign statistics
   * @throws {Error} If fetch fails
   */
  async function fetchCampaignStats(id: number): Promise<CampaignStats> {
    try {
      const stats = await campaignService.getStats(id)
      currentStats.value = stats
      return stats
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Échec du chargement des statistiques'
      throw err
    }
  }

  /**
   * Create a new campaign
   * @param {object} data - Campaign data
   * @param {string} data.name - Campaign name
   * @param {string} data.description - Campaign description
   * @param {string} data.status - Campaign status (draft, active, completed)
   * @param {number[]} data.prospect_ids - Array of prospect IDs to add
   * @returns {Promise<CampaignDetailResponse>} Created campaign
   * @throws {Error} If creation fails
   * @example
   * ```typescript
   * const campaign = await campaignsStore.createCampaign({
   *   name: 'Ma campagne',
   *   description: 'Description',
   *   prospect_ids: [1, 2, 3]
   * });
   * ```
   */
  async function createCampaign(data: {
    name: string
    description?: string
    status?: string
    prospect_ids?: number[]
  }): Promise<CampaignDetailResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign = await campaignService.create(data)

      // Add to campaigns list
      campaigns.value.unshift({
        id: campaign.id,
        user_id: campaign.user_id,
        name: campaign.name,
        description: campaign.description,
        status: campaign.status,
        created_at: campaign.created_at,
        updated_at: campaign.updated_at,
        prospects_count: campaign.prospects_count,
      })

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
   * @param {number} id - Campaign ID
   * @param {object} data - Updated campaign data
   * @param {string} [data.name] - Campaign name
   * @param {string} [data.description] - Campaign description
   * @param {string} [data.status] - Campaign status (draft, active, completed)
   * @returns {Promise<CampaignResponse>} Updated campaign
   * @throws {Error} If update fails
   */
  async function updateCampaign(
    id: number,
    data: {
      name?: string
      description?: string
      status?: string
    },
  ): Promise<CampaignResponse> {
    try {
      isLoading.value = true
      error.value = null

      const campaign = await campaignService.update(id, data)

      // Update in campaigns list
      const index = campaigns.value.findIndex((c) => c.id === id)
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
   * @param {number} id - Campaign ID
   * @returns {Promise<void>} Promise that resolves when deletion is complete
   * @throws {Error} If deletion fails
   */
  async function deleteCampaign(id: number): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      await campaignService.delete(id)

      // Remove from campaigns list
      campaigns.value = campaigns.value.filter((c) => c.id !== id)

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
   * @param {number} campaignId - Campaign ID
   * @param {number[]} prospectIds - Array of prospect IDs to add
   * @returns {Promise<void>} Promise that resolves when prospects are added
   * @throws {Error} If update fails
   */
  async function addProspectsToCampaign(campaignId: number, prospectIds: number[]): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const campaign = await campaignService.addProspects(campaignId, prospectIds)

      // Update current campaign
      currentCampaign.value = campaign

      // Update in campaigns list
      const index = campaigns.value.findIndex((c) => c.id === campaignId)
      if (index !== -1) {
        campaigns.value[index].prospects_count = campaign.prospects_count
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
   * @param {number} campaignId - Campaign ID
   * @param {number} prospectId - Prospect ID to remove
   * @returns {Promise<void>} Promise that resolves when prospect is removed
   * @throws {Error} If update fails
   */
  async function removeProspectFromCampaign(campaignId: number, prospectId: number): Promise<void> {
    try {
      isLoading.value = true
      error.value = null

      const campaign = await campaignService.removeProspect(campaignId, prospectId)

      // Update current campaign
      currentCampaign.value = campaign

      // Update in campaigns list
      const index = campaigns.value.findIndex((c) => c.id === campaignId)
      if (index !== -1) {
        campaigns.value[index].prospects_count = campaign.prospects_count
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
   * @param {number} id - Campaign ID
   * @returns {CampaignResponse | undefined} The campaign or undefined if not found
   */
  function getCampaignById(id: number): CampaignResponse | undefined {
    return campaigns.value.find((c) => c.id === id)
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
