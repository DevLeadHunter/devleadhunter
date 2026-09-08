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

    <div v-if="isLoading" class="flex justify-center py-4">
      <UIcon name="i-lucide-loader-circle" class="h-5 w-5 animate-spin text-[var(--app-faint)]" />
    </div>

    <template v-else>
      <div class="rounded-lg border border-[var(--app-line)] bg-[var(--app-bg)] p-3">
        <div class="mb-2 flex items-center justify-between">
          <p
            class="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-[var(--app-ink-soft)] uppercase"
          >
            <UIcon name="i-lucide-user-round" class="h-3.5 w-3.5" />
            Décisionnaire
          </p>
          <span
            v-if="record?.contact_name_source"
            :class="['app-badge text-[10px]', contactConfidenceBadgeClass]"
            :title="`Confiance : ${Math.round((record?.contact_name_confidence ?? 0) * 100)} %`"
          >
            {{ contactSourceLabel }}
            <template v-if="record?.contact_name_confidence != null">
              · {{ Math.round((record?.contact_name_confidence ?? 0) * 100) }} %
            </template>
          </span>
        </div>

        <div
          v-if="hasPendingProposal"
          class="mb-3 rounded border border-dashed border-[var(--app-accent)]/60 bg-[var(--app-accent-soft)] p-2.5"
        >
          <p class="flex items-center gap-1.5 text-[11px] font-medium text-[var(--app-ink)]">
            <UIcon name="i-lucide-circle-help" class="h-3.5 w-3.5 shrink-0 text-[var(--app-accent-ink)]" />
            Décisionnaire probable : {{ proposedFullName }}
            <span
              v-if="record?.proposed_confidence != null"
              class="text-[10px] font-normal text-[var(--app-accent-ink)]"
            >
              · {{ Math.round((record?.proposed_confidence ?? 0) * 100) }} %
            </span>
          </p>
          <p v-if="record?.proposed_provenance" class="mt-1 text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
            {{ record?.proposed_provenance }}
          </p>
          <p class="mt-1 text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
            Ce nom n'entrera dans aucun email tant qu'il n'est pas confirmé — la salutation reste « Bonjour » neutre.
          </p>
          <div class="mt-2 flex gap-2">
            <button
              type="button"
              class="btn-primary flex-1 text-xs"
              :disabled="isDecidingProposal"
              @click="confirmProposal"
            >
              <UIcon name="i-lucide-check" class="h-3.5 w-3.5" />
              Confirmer
            </button>
            <button
              type="button"
              class="btn-secondary flex-1 text-xs"
              :disabled="isDecidingProposal"
              @click="rejectProposal"
            >
              <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
              Rejeter
            </button>
          </div>
        </div>

        <p
          v-if="record?.contact_name_provenance"
          class="mb-2 flex items-start gap-1.5 text-[10px] leading-relaxed text-[var(--app-ink-soft)]"
        >
          <UIcon name="i-lucide-badge-check" class="mt-0.5 h-3 w-3 shrink-0 text-[var(--app-green)]" />
          {{ record?.contact_name_provenance }}
        </p>

        <p
          v-if="record?.identity_check_detail"
          :class="[
            'mb-2 flex items-start gap-1.5 text-[10px] leading-relaxed',
            isIdentityConflict ? 'text-[var(--app-red)]' : 'text-[var(--app-ink-soft)]',
          ]"
        >
          <UIcon
            :name="isIdentityConflict ? 'i-lucide-shield-alert' : 'i-lucide-shield-check'"
            :class="['mt-0.5 h-3 w-3 shrink-0', isIdentityConflict ? '' : 'text-[var(--app-green)]']"
          />
          {{ record?.identity_check_detail }}
        </p>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Prénom</label>
            <input v-model="form.contact_first_name" type="text" class="input-field" placeholder="Léo" />
          </div>
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Nom</label>
            <input v-model="form.contact_last_name" type="text" class="input-field" placeholder="Guillaume" />
          </div>
        </div>
        <p class="text-muted mt-1.5 text-[10px] leading-relaxed">
          Utilisé pour l'accroche des emails ({salutation}) — vide = « Bonjour » neutre, jamais le nom d'entreprise.
        </p>
        <div class="mt-2 flex gap-2">
          <button type="button" class="btn-secondary flex-1 text-xs" :disabled="isResolving" @click="resolveContact">
            <UIcon
              :name="isResolving ? 'i-lucide-loader-circle' : 'i-lucide-scan-search'"
              :class="['h-3.5 w-3.5', isResolving && 'animate-spin']"
            />
            Rechercher automatiquement
          </button>
          <button
            v-if="contactDirty"
            type="button"
            class="btn-primary shrink-0 text-xs"
            :disabled="isSaving"
            @click="saveContactOnly"
          >
            Enregistrer
          </button>
        </div>
      </div>

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
        <div class="grid grid-cols-2 gap-3">
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Note (/5)</label>
            <input
              v-model.number="form.rating"
              type="number"
              min="0"
              max="5"
              step="0.1"
              class="input-field"
              placeholder="4.8"
            />
          </div>
          <div>
            <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Nb d'avis</label>
            <input v-model.number="form.reviews_count" type="number" min="0" class="input-field" placeholder="27" />
          </div>
        </div>
        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Description</label>
          <textarea
            v-model="form.description"
            rows="2"
            class="input-field"
            placeholder="Plombier chauffagiste à Rennes depuis 2010, dépannage et rénovation…"
          ></textarea>
        </div>

        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Logo (URL)</label>
          <div class="flex items-start gap-2">
            <div
              v-if="trimmedLogoUrl && !hasLogoPreviewError"
              class="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded border border-[var(--app-line)] bg-[var(--app-surface)]"
            >
              <img
                :src="trimmedLogoUrl"
                alt="Aperçu du logo"
                class="h-full w-full object-contain"
                @error="hasLogoPreviewError = true"
              />
            </div>
            <div v-if="isCapturedLogo" class="flex min-w-0 flex-1 items-center gap-2">
              <span class="min-w-0 flex-1 truncate text-[11px] text-[var(--app-ink-soft)]">
                Logo capturé automatiquement — hébergé à la génération
              </span>
              <button
                type="button"
                class="shrink-0 cursor-pointer text-[11px] font-medium text-[var(--app-ink-soft)] underline underline-offset-2 hover:text-[var(--app-ink)]"
                @click="form.logo_url = ''"
              >
                Remplacer
              </button>
            </div>
            <input
              v-else
              v-model="form.logo_url"
              type="url"
              class="input-field min-w-0 flex-1"
              placeholder="https://… — sa couleur de marque personnalise l'action du site généré"
            />
          </div>
          <p
            v-if="trimmedLogoUrl && !isCapturedLogo && hasLogoPreviewError"
            class="mt-1 text-[10px] text-[var(--app-danger)]"
          >
            Image introuvable à cette URL.
          </p>
        </div>

        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Photos ({{ form.photos.length }})</label>
          <p class="mb-2 text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
            Les premières photos sont les plus visibles sur le site. Glissez la poignée ou utilisez les flèches pour
            réordonner.
          </p>
          <TransitionGroup
            v-if="displayedPhotos.length"
            ref="photoGridRef"
            tag="div"
            move-class="transition-transform duration-200 ease-out motion-reduce:transition-none"
            class="relative mb-2 grid grid-cols-3 gap-2"
            role="list"
            aria-label="Photos du prospect, ordonnées pour le site"
          >
            <div
              v-for="(photo, i) in displayedPhotos"
              :key="photo"
              :data-reorder-key="photo"
              role="listitem"
              :class="[
                'group relative rounded border bg-[var(--app-surface)] transition-colors duration-200 ease-out',
                i === 0
                  ? 'border-[var(--app-accent)]'
                  : i === 1
                    ? 'border-[var(--app-accent)]/50'
                    : 'border-[var(--app-line)]',
                draggedPhotoUrl === photo ? 'drag-reorder-slot' : '',
              ]"
            >
              <img
                :src="photo"
                alt=""
                :class="[
                  'w-full cursor-zoom-in rounded-t object-cover',
                  i === 0 ? 'h-20' : i === 1 ? 'h-[4.5rem]' : 'h-16',
                ]"
                draggable="false"
                title="Voir en grand"
                @click="lightboxIndex = i"
              />
              <span
                class="drag-reorder-slot-label pointer-events-none absolute top-1 left-1 flex h-5 min-w-5 items-center justify-center rounded bg-[var(--app-overlay)] px-1 text-[10px] font-semibold text-white tabular-nums"
                aria-hidden="true"
              >
                {{ i + 1 }}
              </span>
              <div
                class="absolute top-1 right-1 flex h-7 w-7 cursor-grab touch-none items-center justify-center rounded bg-[var(--app-overlay)] text-white opacity-100 transition-opacity duration-150 active:cursor-grabbing md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100"
                role="button"
                tabindex="0"
                :aria-label="`Déplacer la photo ${i + 1}`"
                title="Glisser pour réordonner"
                @pointerdown="photoDrag.onGripPointerDown($event, photo)"
              >
                <UIcon name="i-lucide-grip-vertical" class="h-3.5 w-3.5" />
              </div>
              <div class="flex items-center justify-between gap-0.5 border-t border-[var(--app-line)] px-0.5 py-0.5">
                <div class="flex items-center">
                  <button
                    type="button"
                    class="flex h-7 w-7 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors duration-150 hover:bg-[var(--app-bg)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-35"
                    :disabled="i === 0"
                    :aria-label="`Monter la photo ${i + 1}`"
                    title="Monter"
                    @click="movePhoto(i, i - 1)"
                  >
                    <UIcon name="i-lucide-chevron-up" class="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    class="flex h-7 w-7 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors duration-150 hover:bg-[var(--app-bg)] hover:text-[var(--app-ink)] disabled:cursor-not-allowed disabled:opacity-35"
                    :disabled="i >= displayedPhotos.length - 1"
                    :aria-label="`Descendre la photo ${i + 1}`"
                    title="Descendre"
                    @click="movePhoto(i, i + 1)"
                  >
                    <UIcon name="i-lucide-chevron-down" class="h-3.5 w-3.5" />
                  </button>
                </div>
                <div class="flex items-center">
                  <button
                    type="button"
                    class="flex h-7 w-7 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors duration-150 hover:bg-[var(--app-bg)] hover:text-[var(--app-accent-ink)] disabled:cursor-not-allowed disabled:opacity-35"
                    :disabled="i === 0"
                    :aria-label="`Mettre la photo ${i + 1} en premier`"
                    title="Mettre en premier"
                    @click="movePhotoToFront(i)"
                  >
                    <UIcon name="i-lucide-pin" class="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    class="flex h-7 w-7 cursor-pointer items-center justify-center rounded text-[var(--app-ink-soft)] transition-colors duration-150 hover:bg-[var(--app-bg)] hover:text-[var(--app-red)]"
                    :aria-label="`Supprimer la photo ${i + 1}`"
                    title="Supprimer"
                    @click="removePhoto(i)"
                  >
                    <UIcon name="i-lucide-x" class="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </TransitionGroup>
          <div class="flex gap-2">
            <input v-model="newPhotoUrl" type="url" class="input-field flex-1 text-xs" placeholder="URL d'une photo" />
            <button class="btn-secondary px-3 text-xs" @click="addPhoto">Ajouter</button>
          </div>

          <UiImageLightbox v-model="lightboxIndex" :photos="form.photos" />
        </div>

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

        <div>
          <label class="mb-1 block text-[10px] text-[var(--app-ink-soft)]">Horaires</label>
          <div v-if="form.opening_hours.length" class="space-y-1">
            <div
              v-for="(row, i) in form.opening_hours"
              :key="i"
              class="flex items-center gap-2 rounded border border-[var(--app-line)] bg-[var(--app-surface)] px-2 py-1 text-[11px]"
            >
              <span class="w-16 shrink-0 text-[var(--app-ink)] capitalize">{{ row.day }}</span>
              <input
                v-model="row.hours"
                type="text"
                class="input-field flex-1 text-[11px]"
                placeholder="08:00–12:00 ou « Fermé »"
              />
              <button
                class="shrink-0 text-[var(--app-ink-soft)] hover:text-[var(--app-red)]"
                aria-label="Retirer ce jour"
                @click="removeHours(i)"
              >
                <UIcon name="i-lucide-x" class="h-3 w-3" />
              </button>
            </div>
          </div>
          <button v-if="canAddWeekday" class="btn-secondary mt-1.5 w-full text-xs" @click="addWeekday">
            Ajouter un jour
          </button>
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
import type { UseDragToReorderReturn, UseToastReturn } from '~/types/Composables'
import type { EnrichmentForm, UiProspectEnrichmentProps } from '~/types/UiProspectEnrichment'
import type { ComponentPublicInstance, ComputedRef, PropType, Ref } from 'vue'
import type { EnrichmentOpeningHours, ProspectEnrichment } from '~/services/enrichmentService'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { EnrichmentService } from '~/services/enrichmentService'
import { useDragToReorder } from '~/composables/useDragToReorder'
import { useToast } from '~/composables/useToast'

/** Prospect data enrichment form and actions. */
const props: UiProspectEnrichmentProps = defineProps({
  prospectId: {
    type: Number as PropType<number | null>,
    default: null,
  },
  prospectName: {
    type: String,
    default: '',
  },
  prospectCity: {
    type: String,
    default: '',
  },
  prospectGoogleMapsUrl: {
    type: String,
    default: '',
  },
  prospectFacebookUrl: {
    type: String,
    default: '',
  },
  open: {
    type: Boolean,
    required: true,
  },
})

const toast: UseToastReturn = useToast()

const photoDrag: UseDragToReorderReturn<string> = useDragToReorder({
  axis: 'grid',
  getContainer: photoGridElement,
  getOrder: (): string[] => displayedPhotos.value,
  keyOf: (photo: string): string => photo,
  setDraftOrder: (order: string[] | null): void => {
    photosDraft.value = order
  },
  setDraggedKey: (photo: string | null): void => {
    draggedPhotoUrl.value = photo
  },
  onCommit: (order: string[]): void => {
    form.value.photos = order
  },
  liftScale: 1.04,
  morphGhostToSlot: morphPhotoGhostHeight,
})

const record: Ref<ProspectEnrichment | null> = ref(null)
const isLoading: Ref<boolean> = ref(false)
const isRunning: Ref<boolean> = ref(false)
const isSaving: Ref<boolean> = ref(false)
const isResolving: Ref<boolean> = ref(false)
const isDecidingProposal: Ref<boolean> = ref(false)
const newPhotoUrl: Ref<string> = ref('')
/** Index of the photo shown fullscreen in the lightbox, or null when closed. */
const lightboxIndex: Ref<number | null> = ref(null)
const newService: Ref<string> = ref('')
const photoGridRef: Ref<ComponentPublicInstance | null> = ref(null)
/** URL of the photo being dragged, kept until its ghost has landed; null otherwise. */
const draggedPhotoUrl: Ref<string | null> = ref(null)
const photosDraft: Ref<string[] | null> = ref(null)
/** True once the logo URL fails to load, so the broken-image preview is hidden. */
const hasLogoPreviewError: Ref<boolean> = ref(false)

const form: Ref<EnrichmentForm> = ref({
  rating: null,
  reviews_count: null,
  description: '',
  logo_url: '',
  photos: [],
  services: [],
  reviews: [],
  opening_hours: [],
  contact_first_name: '',
  contact_last_name: '',
})

/** Human label of the resolved-contact source badge. */
const CONTACT_SOURCE_LABELS: Record<string, string> = {
  registre_gouv: 'Registre officiel',
  pappers: 'Pappers',
  owner_response: 'Réponse aux avis',
  legal_mentions: 'Mentions légales',
  llm_aggregate: 'IA (texte public)',
  manual: 'Saisie manuelle',
}

const contactSourceLabel: ComputedRef<string> = computed(
  (): string =>
    CONTACT_SOURCE_LABELS[record.value?.contact_name_source ?? ''] ?? record.value?.contact_name_source ?? '',
)

/** Confidence badge tone: green when solid (≥ 80 %), amber when worth an eye. */
const contactConfidenceBadgeClass: ComputedRef<string> = computed((): string =>
  (record.value?.contact_name_confidence ?? 0) >= 0.8 ? 'app-badge--success' : 'app-badge--progress',
)

/** True when the registry and the Maps place disagree (probable homonym). */
const isIdentityConflict: ComputedRef<boolean> = computed(
  (): boolean => record.value?.identity_check_status === 'conflict',
)

/** URL du logo nettoyée : conditionne l'affichage de l'aperçu (vide → pas d'aperçu). */
const trimmedLogoUrl: ComputedRef<string> = computed((): string => form.value.logo_url.trim())

/** Logo capté au scrape en data:base64 (photo de profil Facebook) : on masque le pavé base64 du champ. */
const isCapturedLogo: ComputedRef<boolean> = computed((): boolean => trimmedLogoUrl.value.startsWith('data:'))

/** True when a name proposal awaits the user's confirm/reject decision. */
const hasPendingProposal: ComputedRef<boolean> = computed(
  (): boolean =>
    record.value?.proposed_state === 'pending' &&
    Boolean(record.value?.proposed_first_name || record.value?.proposed_last_name),
)

/** Display name of the pending proposal (« Marie », « Marie Dubois »…). */
const proposedFullName: ComputedRef<string> = computed((): string =>
  [record.value?.proposed_first_name, record.value?.proposed_last_name].filter(Boolean).join(' '),
)

/** True when the contact inputs differ from the stored record (shows Save). */
const contactDirty: ComputedRef<boolean> = computed(
  (): boolean =>
    form.value.contact_first_name !== (record.value?.contact_first_name ?? '') ||
    form.value.contact_last_name !== (record.value?.contact_last_name ?? ''),
)

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

const displayedPhotos: ComputedRef<string[]> = computed((): string[] => photosDraft.value ?? form.value.photos)

/** Copy the loaded record into the editable form. */
function syncForm(): void {
  const r: ProspectEnrichment | null = record.value
  form.value = {
    rating: r?.rating ?? null,
    reviews_count: r?.reviews_count ?? null,
    description: r?.description ?? '',
    logo_url: r?.logo_url ?? '',
    photos: [...(r?.photos ?? [])],
    services: [...(r?.services ?? [])],
    reviews: [...(r?.reviews ?? [])],
    // Deep-copy each row: hours are edited inline, so the form must not mutate the record's objects.
    opening_hours: (r?.opening_hours ?? []).map((row: EnrichmentOpeningHours) => ({ ...row })),
    contact_first_name: r?.contact_first_name ?? '',
    contact_last_name: r?.contact_last_name ?? '',
  }
}

/** Persist ONLY the manual contact edit (works before any enrichment run). */
async function saveContactOnly(): Promise<void> {
  if (!props.prospectId) return
  isSaving.value = true
  try {
    record.value = await EnrichmentService.updateProspectEnrichment(props.prospectId, {
      contact_first_name: form.value.contact_first_name || null,
      contact_last_name: form.value.contact_last_name || null,
    })
    syncForm()
    toast.success('Décisionnaire enregistré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde')
  } finally {
    isSaving.value = false
  }
}

/** Promote the pending name proposal to the trusted contact. */
async function confirmProposal(): Promise<void> {
  if (!props.prospectId) return
  isDecidingProposal.value = true
  try {
    record.value = await EnrichmentService.confirmContactProposal(props.prospectId)
    syncForm()
    toast.success('Décisionnaire confirmé — utilisé dans les prochains emails')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la confirmation')
  } finally {
    isDecidingProposal.value = false
  }
}

/** Reject the pending name proposal (never re-proposed afterwards). */
async function rejectProposal(): Promise<void> {
  if (!props.prospectId) return
  isDecidingProposal.value = true
  try {
    record.value = await EnrichmentService.rejectContactProposal(props.prospectId)
    syncForm()
    toast.success('Proposition rejetée — salutation neutre conservée')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec du rejet')
  } finally {
    isDecidingProposal.value = false
  }
}

/** (Re)run only the decision-maker name resolution. */
async function resolveContact(): Promise<void> {
  if (!props.prospectId) return
  isResolving.value = true
  try {
    record.value = await EnrichmentService.resolveProspectContact(props.prospectId)
    syncForm()
    if (record.value?.contact_first_name || record.value?.contact_last_name) {
      toast.success('Décisionnaire trouvé (source officielle, localisation confirmée)')
    } else if (record.value?.proposed_state === 'pending') {
      toast.success('Nom probable trouvé — à confirmer ci-dessus avant usage')
    } else {
      toast.success('Aucun nom fiable trouvé — salutation neutre conservée')
    }
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Échec de la recherche du décisionnaire')
  } finally {
    isResolving.value = false
  }
}

/** Fetch the enrichment record for the current prospect. */
async function load(): Promise<void> {
  if (!props.prospectId) return
  isLoading.value = true
  try {
    record.value = await EnrichmentService.getProspectEnrichment(props.prospectId)
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
    record.value = await EnrichmentService.runProspectEnrichment(
      props.prospectId,
      props.prospectName,
      props.prospectCity,
      props.prospectGoogleMapsUrl,
      props.prospectFacebookUrl,
    )
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
    // Sent only when changed: an untouched value must not flip the contact_name_manual lock.
    const contactChanged: boolean =
      form.value.contact_first_name !== (record.value?.contact_first_name ?? '') ||
      form.value.contact_last_name !== (record.value?.contact_last_name ?? '')
    record.value = await EnrichmentService.updateProspectEnrichment(props.prospectId, {
      rating: form.value.rating,
      reviews_count: form.value.reviews_count,
      description: form.value.description || null,
      logo_url: form.value.logo_url || null,
      photos: form.value.photos,
      services: form.value.services,
      reviews: form.value.reviews,
      opening_hours: form.value.opening_hours,
      ...(contactChanged
        ? {
            contact_first_name: form.value.contact_first_name || null,
            contact_last_name: form.value.contact_last_name || null,
          }
        : {}),
    })
    syncForm()
    toast.success('Enrichissement enregistré')
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : 'Erreur lors de la sauvegarde')
  } finally {
    isSaving.value = false
  }
}

/** Add a photo URL to the list; a URL already listed is left alone so every tile keeps a unique key. */
function addPhoto(): void {
  const url: string = newPhotoUrl.value.trim()
  if (!url || form.value.photos.includes(url)) return
  form.value.photos.push(url)
  newPhotoUrl.value = ''
}

/** Remove a photo by index. */
function removePhoto(index: number): void {
  form.value.photos.splice(index, 1)
}

/** Move a photo from one index to another, keeping array order for site generation. */
function movePhoto(fromIndex: number, toIndex: number): void {
  const photos: string[] = form.value.photos
  if (fromIndex < 0 || fromIndex >= photos.length) return
  if (toIndex < 0 || toIndex >= photos.length) return
  if (fromIndex === toIndex) return
  const moved: string | undefined = photos.splice(fromIndex, 1)[0]
  if (!moved) return
  photos.splice(toIndex, 0, moved)
}

/** Promote a photo to index 0 (most visible slot on the generated site). */
function movePhotoToFront(index: number): void {
  if (index <= 0) return
  movePhoto(index, 0)
}

/**
 * The rendered photo grid, which is the offsetParent of its tiles.
 * @returns The grid element, or null before it is rendered.
 */
function photoGridElement(): HTMLElement | null {
  const element: unknown = photoGridRef.value?.$el
  return element instanceof HTMLElement ? element : null
}

/**
 * Tiles are taller in the first two slots, so the landing ghost morphs its image to the height of the slot it lands in.
 * @param ghostCard - The lifted copy of the tile.
 * @param slotElement - The tile left in the grid as the landing slot.
 * @param durationMs - Landing duration.
 * @param easing - Landing easing.
 */
function morphPhotoGhostHeight(
  ghostCard: HTMLElement,
  slotElement: HTMLElement,
  durationMs: number,
  easing: string,
): void {
  const ghostImage: HTMLElement | null = ghostCard.querySelector('img')
  const slotImage: HTMLElement | null = slotElement.querySelector('img')
  if (!ghostImage || !slotImage || ghostImage.offsetHeight === slotImage.offsetHeight) return
  const keyframes: Keyframe[] = [{ height: `${ghostImage.offsetHeight}px` }, { height: `${slotImage.offsetHeight}px` }]
  ghostImage.animate(keyframes, { duration: durationMs, easing, fill: 'forwards' })
}

/** Add a service to the list. */
function addService(): void {
  const svc: string = newService.value.trim()
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

const WEEKDAYS: readonly string[] = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']

/**
 * Whether a given weekday is not yet listed in the hours (case-insensitive).
 * @param day Lowercase weekday name to look for.
 * @returns True when no row already carries that day.
 */
function isWeekdayMissing(day: string): boolean {
  return !form.value.opening_hours.some((row: EnrichmentOpeningHours) => (row.day ?? '').toLowerCase() === day)
}

const canAddWeekday: ComputedRef<boolean> = computed((): boolean => WEEKDAYS.some(isWeekdayMissing))

/** Remove an opening-hours row by index. */
function removeHours(index: number): void {
  form.value.opening_hours.splice(index, 1)
}

/** Append the next standard weekday not yet listed, ready to receive its hours. */
function addWeekday(): void {
  const nextDay: string | undefined = WEEKDAYS.find(isWeekdayMissing)
  if (nextDay) {
    form.value.opening_hours.push({ day: nextDay, hours: '' })
  }
}

watch(
  (): [boolean, number | null] => [props.open, props.prospectId],
  ([open, pid]: [boolean, number | null]): void => {
    if (open && pid) {
      void load()
    }
  },
  { immediate: true },
)

// Une nouvelle URL de logo réinitialise l'état d'erreur : on retente l'aperçu.
watch(
  (): string => form.value.logo_url,
  (): void => {
    hasLogoPreviewError.value = false
  },
)

onBeforeUnmount((): void => {
  photoDrag.cancelDrag()
})
</script>
