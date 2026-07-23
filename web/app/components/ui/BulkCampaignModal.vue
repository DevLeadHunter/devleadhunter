<template>
  <Teleport to="body">
    <div
      v-if="open"
      class="fixed inset-0 z-[100] flex items-center justify-center bg-[var(--app-overlay)] p-4 backdrop-blur-sm"
      @click.self="emit('close')"
    >
      <div class="border-muted w-full max-w-md rounded-xl border bg-[var(--app-surface)] p-6">
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <h2 class="text-base font-semibold text-[var(--app-ink)]">Ajouter à une campagne</h2>
            <p class="text-muted mt-1 text-sm">
              {{ prospectIds.length }} prospect{{ prospectIds.length > 1 ? 's' : '' }} sélectionné{{
                prospectIds.length > 1 ? 's' : ''
              }}
            </p>
          </div>
          <button
            type="button"
            class="text-muted cursor-pointer p-1 transition-colors hover:text-[var(--app-ink)]"
            aria-label="Fermer"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div class="mb-4 grid grid-cols-2 gap-2">
          <button
            type="button"
            class="cursor-pointer rounded-lg border px-3 py-2 text-sm font-medium transition-colors"
            :class="
              mode === 'existing'
                ? 'border-[var(--app-green)]/50 bg-[var(--app-green)]/10 text-[var(--app-green)]'
                : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
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
                ? 'border-[var(--app-green)]/50 bg-[var(--app-green)]/10 text-[var(--app-green)]'
                : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]'
            "
            @click="mode = 'new'"
          >
            Nouvelle campagne
          </button>
        </div>

        <div v-if="mode === 'existing'">
          <label class="text-muted mb-1.5 block text-xs font-medium" for="bulk-campaign-select">Campagne</label>
          <div v-if="loading" class="text-muted py-3 text-sm">
            <UIcon name="i-lucide-loader-circle" class="mr-2 h-4 w-4 animate-spin" />Chargement…
          </div>
          <div v-else-if="campaigns.length === 0" class="text-muted py-3 text-sm">
            Aucune campagne. Créez-en une nouvelle.
          </div>
          <select v-else id="bulk-campaign-select" v-model="selectedCampaignId" class="input-field appearance-none">
            <option :value="null" disabled>— Sélectionner —</option>
            <option v-for="c in campaigns" :key="c.id" :value="c.id">{{ c.name }} ({{ c.prospects_count }})</option>
          </select>
        </div>

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

        <p v-if="error" class="mt-3 text-sm text-[var(--app-red)]">{{ error }}</p>

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
            <UIcon v-if="submitting" name="i-lucide-loader-circle" class="h-4 w-4 animate-spin" />
            Ajouter
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script lang="ts" setup>
import type { UseToastReturn } from '~/types/Composables'
import type { ComputedRef, PropType, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { UiBulkCampaignModalProps } from '~/types/UiBulkCampaignModal'
import type { CampaignResponse } from '~/services/campaignService'
import { CampaignService } from '~/services/campaignService'
import { useToast } from '~/composables/useToast'

/** Modal to launch a bulk email campaign on selected prospects. */
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

const emit: {
  (e: 'close'): void
  (e: 'added', payload: { campaignName: string; count: number }): void
} = defineEmits<{
  (e: 'close'): void
  (e: 'added', payload: { campaignName: string; count: number }): void
}>()

const toast: UseToastReturn = useToast()

/** Whether to add to an existing campaign or create a new one. */
const mode: Ref<'existing' | 'new'> = ref('existing')

/** Campaigns available to pick from. */
const campaigns: Ref<CampaignResponse[]> = ref([])

/** Selected existing campaign id. */
const selectedCampaignId: Ref<number | null> = ref(null)

/** New campaign name (create mode). */
const newName: Ref<string> = ref('')

/** Whether the campaign list is loading. */
const loading: Ref<boolean> = ref(false)

/** Whether a submit is in flight. */
const submitting: Ref<boolean> = ref(false)

/** Inline error message. */
const error: Ref<string | null> = ref(null)

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
    const res = await CampaignService.list(0, 100)
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
      const created = await CampaignService.create({ name: newName.value.trim() })
      campaignId = created.id
      campaignName = created.name
    } else {
      campaignId = selectedCampaignId.value as number
      campaignName = campaigns.value.find((c: CampaignResponse): boolean => c.id === campaignId)?.name ?? 'campagne'
    }

    await CampaignService.addProspects(campaignId, props.prospectIds)
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
