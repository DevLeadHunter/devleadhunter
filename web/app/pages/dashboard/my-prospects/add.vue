<template>
  <div class="mx-auto max-w-3xl space-y-6">
    <div>
      <NuxtLink
        to="/dashboard/my-prospects"
        class="inline-flex items-center gap-2 text-sm text-[#8b949e] transition hover:text-[#f9f9f9]"
      >
        <i class="fa-solid fa-arrow-left text-xs"></i>
        Retour aux prospects
      </NuxtLink>
      <h1 class="mt-4 text-2xl font-semibold text-[#f9f9f9]">Ajouter un prospect</h1>
      <p class="text-muted mt-2 text-sm">
        Saisissez le nom de l'entreprise et/ou le lien Google Maps pour pré-remplir automatiquement.
      </p>
    </div>

    <div class="card space-y-6 p-6 md:p-8">
      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium">Nom de l'entreprise</label>
        <UiBusinessSearchInput ref="businessSearchRef" :city="addForm.city" @select="handleBusinessSelect" />
        <p class="text-muted mt-1 text-xs">Tapez le nom puis sélectionnez une entreprise dans la liste.</p>
      </div>

      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium">Lien fiche Google Maps</label>
        <input
          v-model="addForm.google_maps_url"
          type="url"
          class="input-field"
          placeholder="https://maps.app.goo.gl/..."
        />
      </div>

      <div>
        <label class="text-muted mb-1.5 block text-xs font-medium">Ville (optionnel)</label>
        <input v-model="addForm.city" type="text" class="input-field" placeholder="Paris" />
        <p class="text-muted mt-1 text-xs">Affine les suggestions quand vous recherchez par nom d'entreprise.</p>
      </div>

      <button
        type="button"
        class="btn-primary h-9 min-h-9 w-full px-4 text-sm disabled:cursor-not-allowed"
        :disabled="isEnriching || !canEnrichProspect"
        @click="handleEnrichProspect"
      >
        <i v-if="isEnriching" class="fa-solid fa-spinner fa-spin mr-2"></i>
        {{ isEnriching ? 'Récupération depuis Google…' : 'Pré-remplir depuis Google' }}
      </button>

      <div v-if="enrichError" class="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
        {{ enrichError }}
      </div>

      <div class="space-y-4 rounded-lg border border-[#30363d] bg-[#050505] p-4">
        <h2 class="text-sm font-medium text-[#f9f9f9]">Informations du prospect</h2>
        <div class="grid gap-4 md:grid-cols-2">
          <div class="md:col-span-2">
            <label class="text-muted mb-1.5 block text-xs font-medium">Nom *</label>
            <input v-model="prospectDraft.name" type="text" class="input-field" required />
          </div>
          <div class="md:col-span-2">
            <label class="text-muted mb-1.5 block text-xs font-medium">Adresse</label>
            <input v-model="prospectDraft.address" type="text" class="input-field" />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Ville</label>
            <input v-model="prospectDraft.city" type="text" class="input-field" />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Catégorie</label>
            <input v-model="prospectDraft.category" type="text" class="input-field" />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Téléphone</label>
            <input v-model="prospectDraft.phone" type="text" class="input-field" />
          </div>
          <div>
            <label class="text-muted mb-1.5 block text-xs font-medium">Email</label>
            <input v-model="prospectDraft.email" type="email" class="input-field" />
          </div>
          <div class="md:col-span-2">
            <label class="text-muted mb-1.5 block text-xs font-medium">Site web</label>
            <input v-model="prospectDraft.website" type="url" class="input-field" />
          </div>
        </div>
        <p class="text-muted text-xs">Score de confiance : {{ prospectDraft.confidence }}/4</p>
      </div>

      <div class="flex flex-wrap justify-end gap-3">
        <NuxtLink to="/dashboard/my-prospects" class="btn-secondary">Annuler</NuxtLink>
        <button
          type="button"
          class="btn-primary disabled:cursor-not-allowed"
          :disabled="isCreatingProspect || !canSaveProspect"
          @click="handleCreateProspect"
        >
          {{ isCreatingProspect ? 'Ajout en cours…' : 'Ajouter le prospect' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { ManualProspectAddForm, ProspectCreatePayload, ProspectSearchSuggestion } from '~/types'
import type { BusinessSearchInputExpose } from '~/types/BusinessSearchInput'
import { createProspect, enrichProspect } from '~/services/prospectsService'

definePageMeta({
  layout: 'dashboard',
  middleware: ['auth'],
})

const router = useRouter()

const businessSearchRef: Ref<BusinessSearchInputExpose | null> = ref<BusinessSearchInputExpose | null>(null)
const isEnriching: Ref<boolean> = ref<boolean>(false)
const isCreatingProspect: Ref<boolean> = ref<boolean>(false)
const enrichError: Ref<string | null> = ref<string | null>(null)
const addForm: Ref<ManualProspectAddForm> = ref<ManualProspectAddForm>({
  business_name: '',
  google_maps_url: '',
  city: '',
})
const prospectDraft: Ref<ProspectCreatePayload> = ref<ProspectCreatePayload>(createEmptyProspectDraft())

const canEnrichProspect: ComputedRef<boolean> = computed((): boolean => {
  return Boolean(addForm.value.business_name.trim() || addForm.value.google_maps_url.trim())
})

const canSaveProspect: ComputedRef<boolean> = computed((): boolean => {
  return Boolean(prospectDraft.value.name.trim() && prospectDraft.value.category.trim())
})

function createEmptyProspectDraft(): ProspectCreatePayload {
  return {
    name: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    website: '',
    category: 'Entreprise',
    source: 'google',
    confidence: 1,
  }
}

/**
 * Applique une suggestion Google Maps sélectionnée puis lance l'enrichissement.
 * @param suggestion - Entreprise sélectionnée dans l'autocomplete.
 * @returns void
 */
function handleBusinessSelect(suggestion: ProspectSearchSuggestion): void {
  addForm.value.business_name = suggestion.label
  addForm.value.google_maps_url = suggestion.google_maps_url
  void handleEnrichProspect()
}

async function handleEnrichProspect(): Promise<void> {
  if (!canEnrichProspect.value) {
    return
  }

  isEnriching.value = true
  enrichError.value = null
  try {
    const result = await enrichProspect({
      business_name: addForm.value.business_name.trim() || undefined,
      google_maps_url: addForm.value.google_maps_url.trim() || undefined,
      city: addForm.value.city.trim() || undefined,
    })
    prospectDraft.value = {
      ...result,
      address: result.address ?? '',
      city: result.city ?? '',
      phone: result.phone ?? '',
      email: result.email ?? '',
      website: result.website ?? '',
    }
  } catch (err: unknown) {
    enrichError.value = err instanceof Error ? err.message : 'Impossible de récupérer la fiche Google'
  } finally {
    isEnriching.value = false
  }
}

async function handleCreateProspect(): Promise<void> {
  if (!canSaveProspect.value) {
    return
  }

  isCreatingProspect.value = true
  enrichError.value = null
  try {
    await createProspect({
      name: prospectDraft.value.name.trim(),
      address: prospectDraft.value.address?.trim() || null,
      city: prospectDraft.value.city?.trim() || null,
      phone: prospectDraft.value.phone?.trim() || null,
      email: prospectDraft.value.email?.trim() || null,
      website: prospectDraft.value.website?.trim() || null,
      category: prospectDraft.value.category.trim(),
      source: prospectDraft.value.source,
      confidence: prospectDraft.value.confidence,
    })
    await router.push('/dashboard/my-prospects')
  } catch (err: unknown) {
    enrichError.value = err instanceof Error ? err.message : "Impossible d'ajouter le prospect"
  } finally {
    isCreatingProspect.value = false
  }
}
</script>
