<template>
  <div class="space-y-3 px-5 py-4">
    <div class="flex items-center justify-between">
      <p class="text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase">Enrichissement</p>
      <span
        v-if="record"
        :class="['inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium', statusClass]"
      >
        {{ statusLabel }}
      </span>
    </div>

    <p class="text-xs text-[var(--app-ink-soft)]">
      Données riches (photos, avis, horaires, note) utilisées pour générer le site. Séparé de la recherche de prospects.
    </p>

    <!-- Initial / empty state -->
    <div v-if="isLoading" class="flex justify-center py-4">
      <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-faint)]" />
    </div>

    <template v-else>
      <button
        v-if="!record || record.status === 'pending'"
        class="btn-secondary w-full"
        :disabled="isRunning"
        @click="run"
      >
        <UIcon
          :name="isRunning ? 'i-lucide-loader-circle' : 'i-lucide-wand-sparkles'"
          :class="['h-4 w-4', isRunning && 'animate-spin']"
        />
        Récupérer les données
      </button>

      <template v-else>
        <!-- Rating + reviews count + description -->
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Note (/5)</label>
            <input v-model.number="form.rating" type="number" min="0" max="5" step="0.1" class="input-field" />
          </div>
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Nb d'avis</label>
            <input v-model.number="form.reviews_count" type="number" min="0" class="input-field" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Description</label>
          <textarea v-model="form.description" rows="2" class="input-field"></textarea>
        </div>

        <!-- Photos -->
        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Photos ({{ form.photos.length }})</label>
          <div v-if="form.photos.length" class="mb-2 grid grid-cols-3 gap-2">
            <div v-for="(photo, i) in form.photos" :key="i" class="group relative">
              <img :src="photo" alt="" class="h-16 w-full rounded border border-[var(--app-line)] object-cover" />
              <button
                class="absolute top-0.5 right-0.5 flex h-5 w-5 items-center justify-center rounded bg-[var(--app-overlay)] text-white opacity-0 transition-opacity group-hover:opacity-100"
                @click="removePhoto(i)"
              >
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </div>
          </div>
          <div class="flex gap-2">
            <input v-model="newPhotoUrl" type="url" class="input-field flex-1 text-xs" placeholder="URL d'une photo" />
            <button class="btn-secondary px-3 text-xs" @click="addPhoto">Ajouter</button>
          </div>
        </div>

        <!-- Services -->
        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Services</label>
          <div v-if="form.services.length" class="mb-2 flex flex-wrap gap-1.5">
            <span
              v-for="(svc, i) in form.services"
              :key="i"
              class="inline-flex items-center gap-1 rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-0.5 text-xs text-[var(--app-ink)]"
            >
              {{ svc }}
              <button class="text-[var(--app-ink-soft)] hover:text-[var(--app-red)]" @click="removeService(i)">
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </span>
          </div>
          <div class="flex gap-2">
            <input
              v-model="newService"
              type="text"
              class="input-field flex-1 text-xs"
              placeholder="Ajouter un service"
            />
            <button class="btn-secondary px-3 text-xs" @click="addService">Ajouter</button>
          </div>
        </div>

        <!-- Reviews (read-only, removable) -->
        <div v-if="form.reviews.length">
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Avis ({{ form.reviews.length }})</label>
          <div class="space-y-1.5">
            <div
              v-for="(review, i) in form.reviews"
              :key="i"
              class="flex items-start gap-2 rounded border border-[var(--app-line)] bg-[var(--app-surface)] p-2"
            >
              <div class="min-w-0 flex-1">
                <p class="text-[10px] font-medium text-[var(--app-ink)]">{{ review.author || 'Client' }}</p>
                <p class="line-clamp-2 text-[11px] text-[var(--app-ink-soft)]">{{ review.text }}</p>
              </div>
              <button class="text-[var(--app-ink-soft)] hover:text-[var(--app-red)]" @click="removeReview(i)">
                <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>

        <!-- Opening hours (read-only, removable) -->
        <div v-if="form.opening_hours.length">
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Horaires</label>
          <div class="space-y-1">
            <div
              v-for="(row, i) in form.opening_hours"
              :key="i"
              class="flex items-center justify-between rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-1 text-[11px]"
            >
              <span class="text-[var(--app-ink)]">{{ row.day }}</span>
              <span class="text-[var(--app-ink-soft)]">{{ row.hours }}</span>
              <button class="text-[var(--app-ink-soft)] hover:text-[var(--app-red)]" @click="removeHours(i)">
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </div>
          </div>
        </div>

        <p v-if="record.error_message" class="text-[11px] text-[var(--app-red)]">{{ record.error_message }}</p>

        <div class="flex gap-2 pt-1">
          <button class="btn-secondary flex-1 text-xs" :disabled="isRunning" @click="run">
            <UIcon
              :name="isRunning ? 'i-lucide-loader-circle' : 'i-lucide-rotate-cw'"
              :class="['h-3.5 w-3.5', isRunning && 'animate-spin']"
            />
            Relancer
          </button>
          <button class="btn-primary flex-1 text-xs" :disabled="isSaving" @click="save">
            <UIcon v-if="isSaving" name="i-lucide-loader-circle" class="h-3.5 w-3.5 animate-spin" />
            Enregistrer
          </button>
        </div>
      </template>
    </template>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import { ref, computed, watch } from 'vue'
import type { EnrichmentOpeningHours, EnrichmentReview, ProspectEnrichment } from '~/services/enrichmentService'
import { getProspectEnrichment, runProspectEnrichment, updateProspectEnrichment } from '~/services/enrichmentService'
import type { UiProspectEnrichmentProps } from '~/types/UiProspectEnrichment'
import { useToast } from '~/composables/useToast'

/**
 * Définit les props du composant UiProspectEnrichment.
 */
const props: UiProspectEnrichmentProps = defineProps({
  prospectId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  open: {
    type: Boolean,
    required: true,
  },
})

const toast = useToast()

const record: Ref<ProspectEnrichment | null> = ref<ProspectEnrichment | null>(null)
const isLoading: Ref<boolean> = ref(false)
const isRunning: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const newPhotoUrl: Ref<string> = ref('')
const newService: Ref<string> = ref('')

interface EnrichmentForm {
  rating: number | null
  reviews_count: number | null
  description: string
  photos: string[]
  services: string[]
  reviews: EnrichmentReview[]
  opening_hours: EnrichmentOpeningHours[]
}

const form: Ref<EnrichmentForm> = ref<EnrichmentForm>({
  rating: null,
  reviews_count: null,
  description: '',
  photos: [],
  services: [],
  reviews: [],
  opening_hours: [],
})

const STATUS_LABELS: Record<string, string> = {
  pending: 'À récupérer',
  enriching: 'En cours…',
  completed: 'Récupéré',
  failed: 'Échec',
}

const statusLabel: ComputedRef<string> = computed((): string => STATUS_LABELS[record.value?.status ?? ''] ?? '')
const statusClass: ComputedRef<string> = computed((): string => {
  switch (record.value?.status) {
    case 'completed':
      return 'border border-[var(--app-green)]/40 bg-[var(--app-green)]/10 text-[var(--app-green)]'
    case 'failed':
      return 'border border-[var(--app-red)]/40 bg-[var(--app-red)]/10 text-[var(--app-red)]'
    default:
      return 'border border-[var(--app-line)] bg-[var(--app-surface)] text-[var(--app-ink-soft)]'
  }
})

/** Copy the loaded record into the editable form. */
function syncForm(): void {
  const r = record.value
  form.value = {
    rating: r?.rating ?? null,
    reviews_count: r?.reviews_count ?? null,
    description: r?.description ?? '',
    photos: [...(r?.photos ?? [])],
    services: [...(r?.services ?? [])],
    reviews: [...(r?.reviews ?? [])],
    opening_hours: [...(r?.opening_hours ?? [])],
  }
}

/** Fetch the enrichment record for the current prospect. */
async function load(): Promise<void> {
  if (!props.prospectId) return
  isLoading.value = true
  try {
    record.value = await getProspectEnrichment(props.prospectId)
    syncForm()
  } finally {
    isLoading.value = false
  }
}

/** Run (or re-run) the enrichment scraper. */
async function run(): Promise<void> {
  if (!props.prospectId) return
  isRunning.value = true
  try {
    record.value = await runProspectEnrichment(props.prospectId)
    syncForm()
    toast.success('Données récupérées')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Échec de l'enrichissement")
  } finally {
    isRunning.value = false
  }
}

/** Persist manual edits. */
async function save(): Promise<void> {
  if (!props.prospectId) return
  isSaving.value = true
  try {
    record.value = await updateProspectEnrichment(props.prospectId, {
      rating: form.value.rating,
      reviews_count: form.value.reviews_count,
      description: form.value.description || null,
      photos: form.value.photos,
      services: form.value.services,
      reviews: form.value.reviews,
      opening_hours: form.value.opening_hours,
    })
    syncForm()
    toast.success('Enrichissement enregistré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde')
  } finally {
    isSaving.value = false
  }
}

/** Add a photo URL to the list. */
function addPhoto(): void {
  const url = newPhotoUrl.value.trim()
  if (url) {
    form.value.photos.push(url)
    newPhotoUrl.value = ''
  }
}

/** Remove a photo by index. */
function removePhoto(index: number): void {
  form.value.photos.splice(index, 1)
}

/** Add a service to the list. */
function addService(): void {
  const svc = newService.value.trim()
  if (svc) {
    form.value.services.push(svc)
    newService.value = ''
  }
}

/** Remove a service by index. */
function removeService(index: number): void {
  form.value.services.splice(index, 1)
}

/** Remove a review by index. */
function removeReview(index: number): void {
  form.value.reviews.splice(index, 1)
}

/** Remove an opening-hours row by index. */
function removeHours(index: number): void {
  form.value.opening_hours.splice(index, 1)
}

watch(
  (): [boolean, number | null] => [props.open, props.prospectId],
  ([open, pid]): void => {
    if (open && pid) {
      void load()
    }
  },
  { immediate: true },
)
</script>
