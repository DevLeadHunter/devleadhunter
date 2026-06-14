<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="border-muted w-full max-w-md rounded-xl border bg-[#1a1a1a] p-6">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 class="text-base font-semibold text-[#f9f9f9]">Ajouter à une campagne</h2>
            <p class="text-muted mt-1 text-sm">
              {{ prospectIds.length }} prospect{{ prospectIds.length > 1 ? 's' : '' }} sélectionné{{
                prospectIds.length > 1 ? 's' : ''
              }}
            </p>
          </div>
          <button
            type="button"
            class="text-muted cursor-pointer p-1 transition-colors hover:text-[#f9f9f9]"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <i class="fa-solid fa-times"></i>
          </button>
        </div>

        <!-- Mode toggle -->
        <div class="mb-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            class="cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium transition-colors"
            :class="
              mode === 'existing'
                ? 'border-[#2BAD5F]/50 bg-[#2BAD5F]/10 text-[#3fb950]'
                : 'border-[#30363d] text-[#8b949e] hover:text-[#f9f9f9]'
            "
            @click="mode = 'existing'"
          >
            Campagne existante
          </button>
          <button
            type="button"
            class="cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium transition-colors"
            :class="
              mode === 'new'
                ? 'border-[#2BAD5F]/50 bg-[#2BAD5F]/10 text-[#3fb950]'
                : 'border-[#30363d] text-[#8b949e] hover:text-[#f9f9f9]'
            "
            @click="mode = 'new'"
          >
            Nouvelle campagne
          </button>
        </div>

        <!-- Existing campaign -->
        <div v-if="mode === 'existing'">
          <label class="text-muted mb-1.5 block text-xs font-medium" for="bulk-campaign-select">Campagne</label>
          <div v-if="loading" class="text-muted py-3 text-sm">
            <i class="fa-solid fa-spinner fa-spin mr-2"></i>Chargement…
          </div>
          <div v-else-if="campaigns.length === 0" class="text-muted py-3 text-sm">
            Aucune campagne. Créez-en une nouvelle.
          </div>
          <select v-else id="bulk-campaign-select" v-model="selectedCampaignId" class="input-field appearance-none">
            <option :value="null" disabled>— Sélectionner —</option>
            <option v-for="c in campaigns" :key="c.id" :value="c.id">{{ c.name }} ({{ c.prospects_count }})</option>
          </select>
        </div>

        <!-- New campaign -->
        <div v-else>
          <label class="text-muted mb-1.5 block text-xs font-medium" for="bulk-campaign-name">Nom de la campagne</label>
          <input
            id="bulk-campaign-name"
            v-model="newName"
            type="text"
            placeholder="Ex : Plombiers Lyon — juin"
            class="input-field"
          />
        </div>

        <p v-if="error" class="mt-3 text-sm text-[#DC4747]">{{ error }}</p>

        <div class="mt-6 flex gap-3">
          <button type="button" class="btn-secondary flex-1" :disabled="submitting" @click="emit('close')">
            Annuler
          </button>
          <button
            type="button"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="submitting || !canSubmit"
            @click="submit"
          >
            <i v-if="submitting" class="fa-solid fa-spinner fa-spin mr-2"></i>
            Ajouter
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { UiBulkCampaignModalProps } from '~/types/UiBulkCampaignModal'
import { campaignService, type CampaignResponse } from '~/services/campaignService'
import { useToast } from '~/composables/useToast'

/**
 * Defines the component props.
 */
const props: UiBulkCampaignModalProps = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  prospectIds: {
    type: Array as PropType<number[]>,
    required: true,
  },
})

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'added', payload: { campaignName: string; count: number }): void
}>()

const toast = useToast()

/** Whether to add to an existing campaign or create a new one. */
const mode: Ref<'existing' | 'new'> = ref<'existing' | 'new'>('existing')

/** Campaigns available to pick from. */
const campaigns: Ref<CampaignResponse[]> = ref<CampaignResponse[]>([])

/** Selected existing campaign id. */
const selectedCampaignId: Ref<number | null> = ref<number | null>(null)

/** New campaign name (create mode). */
const newName: Ref<string> = ref<string>('')

/** Whether the campaign list is loading. */
const loading: Ref<boolean> = ref<boolean>(false)

/** Whether a submit is in flight. */
const submitting: Ref<boolean> = ref<boolean>(false)

/** Inline error message. */
const error: Ref<string | null> = ref<string | null>(null)

/** Whether the form can be submitted. */
const canSubmit: ComputedRef<boolean> = computed((): boolean => {
  if (props.prospectIds.length === 0) return false
  return mode.value === 'new' ? newName.value.trim().length >= 2 : selectedCampaignId.value !== null
})

/**
 * Load the user's campaigns to populate the existing-campaign select.
 */
async function loadCampaigns(): Promise<void> {
  try {
    loading.value = true
    const res = await campaignService.list(0, 100)
    campaigns.value = res.campaigns
    if (campaigns.value.length === 0) mode.value = 'new'
  } catch {
    campaigns.value = []
  } finally {
    loading.value = false
  }
}

/**
 * Add the selected prospects to the chosen (or newly created) campaign.
 */
async function submit(): Promise<void> {
  if (!canSubmit.value || submitting.value) return
  error.value = null
  submitting.value = true
  try {
    let campaignId: number
    let campaignName: string

    if (mode.value === 'new') {
      const created = await campaignService.create({ name: newName.value.trim() })
      campaignId = created.id
      campaignName = created.name
    } else {
      campaignId = selectedCampaignId.value as number
      campaignName = campaigns.value.find((c: CampaignResponse): boolean => c.id === campaignId)?.name ?? 'campagne'
    }

    await campaignService.addProspects(campaignId, props.prospectIds)
    emit('added', { campaignName, count: props.prospectIds.length })
    emit('close')
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : "Erreur lors de l'ajout à la campagne"
    toast.error(error.value)
  } finally {
    submitting.value = false
  }
}

watch(
  (): boolean => props.open,
  (isOpen: boolean): void => {
    if (isOpen) {
      mode.value = 'existing'
      selectedCampaignId.value = null
      newName.value = ''
      error.value = null
      loadCampaigns()
    }
  },
)
</script>
