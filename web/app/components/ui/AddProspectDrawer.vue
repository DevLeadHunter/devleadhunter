<template>
  <Teleport to="body">
    <!-- Pas de backdrop : drawer non-modal (navigation possible pendant qu'il
         est ouvert), fermeture par X / Échap. -->
    <Transition name="drawer-panel">
      <div
        v-if="open"
        class="fixed top-0 right-0 z-50 flex h-dvh w-full max-w-[480px] flex-col border-l border-[var(--app-line)] bg-[var(--app-surface)] shadow-2xl"
      >
        <!-- ───────────────────────── Header ───────────────────────── -->
        <div class="flex items-start gap-3 border-b border-[var(--app-line)] px-5 py-4">
          <button
            v-if="showBack"
            class="flex h-10 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            title="Revenir au volet précédent"
            @click="emit('back')"
          >
            <UIcon name="i-lucide-chevron-left" class="h-4 w-4" />
          </button>

          <span
            class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--app-line)] bg-[var(--app-surface-2)]"
          >
            <UIcon name="i-lucide-user-plus" class="h-4 w-4 text-[var(--app-ink-soft)]" />
          </span>

          <div class="min-w-0 flex-1">
            <h2 class="text-base leading-tight font-semibold text-[var(--app-ink)]">Ajouter un prospect</h2>
            <p class="mt-0.5 truncate text-[11px] text-[var(--app-ink-soft)]">
              Pré-remplissez depuis Google ou saisissez à la main
            </p>
          </div>

          <button
            class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors hover:bg-[var(--app-surface-2)] hover:text-[var(--app-ink)]"
            @click="emit('close')"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <!-- ───────────────────────── Body ────────────────────────── -->
        <div class="flex-1 space-y-5 overflow-y-auto px-5 py-4">
          <!-- Étape 1 — pré-remplissage Google (optionnel) -->
          <div class="space-y-3">
            <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
              1 · Pré-remplir depuis Google (optionnel)
            </p>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium">Nom de l'entreprise</label>
              <UiBusinessSearchInput ref="businessSearchRef" :city="addForm.city" @select="handleBusinessSelect" />
              <p class="text-muted mt-1 text-xs">Tapez le nom puis sélectionnez une entreprise dans la liste.</p>
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="drawer-gmaps-url">
                Ou lien fiche Google Maps
              </label>
              <input
                id="drawer-gmaps-url"
                v-model="addForm.google_maps_url"
                type="url"
                class="input-field"
                placeholder="https://maps.app.goo.gl/..."
              />
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="drawer-add-city">
                Ville (affine la recherche)
              </label>
              <UiCityAutocompleteInput v-model="addForm.city" input-id="drawer-add-city" placeholder="Paris" />
            </div>
            <button
              type="button"
              class="btn-secondary w-full disabled:cursor-not-allowed disabled:opacity-50"
              :disabled="isEnriching || !canEnrichProspect"
              @click="handleEnrichProspect"
            >
              <UIcon
                :name="isEnriching ? 'i-lucide-loader-circle' : 'i-lucide-wand-sparkles'"
                :class="['h-4 w-4', isEnriching && 'animate-spin']"
              />
              {{ isEnriching ? 'Récupération depuis Google…' : 'Pré-remplir depuis Google' }}
            </button>
            <p
              v-if="enrichError"
              class="rounded-lg border border-[var(--app-red)]/30 bg-[var(--app-red-soft)] px-3 py-2 text-xs text-[var(--app-red)]"
            >
              {{ enrichError }}
            </p>
          </div>

          <!-- Étape 2 — informations du prospect -->
          <form
            id="add-prospect-form"
            class="space-y-3 border-t border-[var(--app-line-soft)] pt-4"
            @submit.prevent="handleCreateProspect"
          >
            <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">
              2 · Informations du prospect
            </p>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-name">
                Nom <span class="text-[var(--app-accent)]">*</span>
              </label>
              <input id="draft-name" v-model="prospectDraft.name" type="text" class="input-field" required />
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-category">
                Catégorie (métier) <span class="text-[var(--app-accent)]">*</span>
              </label>
              <input
                id="draft-category"
                v-model="prospectDraft.category"
                type="text"
                class="input-field"
                placeholder="plombier, électricien…"
                required
              />
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-address">Adresse</label>
              <input id="draft-address" v-model="prospectDraft.address" type="text" class="input-field" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-city-input">Ville</label>
                <UiCityAutocompleteInput v-model="prospectDraft.city" input-id="draft-city-input" />
              </div>
              <div>
                <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-phone">Téléphone</label>
                <input id="draft-phone" v-model="prospectDraft.phone" type="text" class="input-field" />
              </div>
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-email">Email</label>
              <input id="draft-email" v-model="prospectDraft.email" type="email" class="input-field" />
            </div>
            <div>
              <label class="text-muted mb-1.5 block text-xs font-medium" for="draft-website">Site web</label>
              <input
                id="draft-website"
                v-model="prospectDraft.website"
                type="url"
                class="input-field"
                placeholder="Laissez vide si le prospect n'a pas de site"
              />
            </div>
          </form>
        </div>

        <!-- ───────────────────────── Footer ─────────────────────── -->
        <div class="flex gap-2 border-t border-[var(--app-line)] px-5 py-4">
          <button type="button" class="btn-secondary flex-1" :disabled="isCreatingProspect" @click="emit('close')">
            Annuler
          </button>
          <button
            type="submit"
            form="add-prospect-form"
            class="btn-primary flex-1 disabled:cursor-not-allowed disabled:opacity-50"
            :disabled="isCreatingProspect || !canSaveProspect"
          >
            <UIcon v-if="isCreatingProspect" name="i-lucide-loader-circle" class="mr-1.5 h-4 w-4 animate-spin" />
            {{ isCreatingProspect ? 'Ajout…' : 'Ajouter le prospect' }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import { computed, ref, watch } from 'vue'
import type { Prospect, ProspectCreatePayload, ProspectSearchSuggestion } from '~/types'
import type { BusinessSearchInputExpose } from '~/types/BusinessSearchInput'
import { createProspect, enrichProspect } from '~/services/prospectsService'
import { useToast } from '~/composables/useToast'

/** Local shape of the Google prefill form. */
interface AddProspectPrefillForm {
  business_name: string
  google_maps_url: string
  city: string
}

/**
 * Defines the component props.
 */
const props = defineProps({
  open: {
    type: Boolean,
    required: true,
  },
  showBack: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits<{
  /** Close every drawer. */
  close: []
  /** Go back to the previous drawer of the stack. */
  back: []
  /** Prospect created — the host chains to its detail drawer. */
  created: [prospect: Prospect]
}>()

const toast = useToast()

const businessSearchRef: Ref<BusinessSearchInputExpose | null> = ref<BusinessSearchInputExpose | null>(null)
const isEnriching: Ref<boolean> = ref<boolean>(false)
const isCreatingProspect: Ref<boolean> = ref<boolean>(false)
const enrichError: Ref<string | null> = ref<string | null>(null)
const addForm: Ref<AddProspectPrefillForm> = ref<AddProspectPrefillForm>({
  business_name: '',
  google_maps_url: '',
  city: '',
})
const prospectDraft: Ref<ProspectCreatePayload> = ref<ProspectCreatePayload>(createEmptyProspectDraft())

/** Whether the Google prefill can run (name or Maps link present). */
const canEnrichProspect: ComputedRef<boolean> = computed((): boolean => {
  return Boolean(addForm.value.business_name.trim() || addForm.value.google_maps_url.trim())
})

/** Whether the draft is complete enough to be saved. */
const canSaveProspect: ComputedRef<boolean> = computed((): boolean => {
  return Boolean(prospectDraft.value.name.trim() && prospectDraft.value.category.trim())
})

/**
 * Build a blank prospect draft (manual source until Google prefills it).
 * @returns An empty create payload.
 */
function createEmptyProspectDraft(): ProspectCreatePayload {
  return {
    name: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    website: '',
    category: '',
    source: 'manual',
    confidence: 1,
  }
}

/**
 * Apply a selected Google Maps suggestion then run the prefill.
 * @param suggestion - Business picked in the autocomplete.
 */
function handleBusinessSelect(suggestion: ProspectSearchSuggestion): void {
  addForm.value.business_name = suggestion.label
  addForm.value.google_maps_url = suggestion.google_maps_url
  void handleEnrichProspect()
}

/**
 * Fetch public business details from Google and prefill the draft.
 * @returns A promise resolved once the prefill completes (or fails).
 */
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

/**
 * Create the prospect, then hand it to the host (which opens its detail drawer).
 * @returns A promise resolved once the prospect is created.
 */
async function handleCreateProspect(): Promise<void> {
  if (!canSaveProspect.value) {
    return
  }
  isCreatingProspect.value = true
  enrichError.value = null
  try {
    const created: Prospect = await createProspect({
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
    toast.success(`« ${created.name} » ajouté à vos prospects`)
    emit('created', created)
  } catch (err: unknown) {
    enrichError.value = err instanceof Error ? err.message : "Impossible d'ajouter le prospect"
  } finally {
    isCreatingProspect.value = false
  }
}

watch(
  (): boolean => props.open,
  (open: boolean): void => {
    if (open) {
      addForm.value = { business_name: '', google_maps_url: '', city: '' }
      prospectDraft.value = createEmptyProspectDraft()
      enrichError.value = null
      businessSearchRef.value?.reset()
    }
  },
)
</script>

<style scoped>
.drawer-panel-enter-active,
.drawer-panel-leave-active {
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.drawer-panel-enter-from,
.drawer-panel-leave-to {
  transform: translateX(100%);
}
</style>
