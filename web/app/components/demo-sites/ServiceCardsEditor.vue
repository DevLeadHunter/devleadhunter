<template>
  <div class="space-y-4">
    <div class="flex items-start justify-between gap-3">
      <div>
        <p class="app-label">{{ config.heading }}</p>
        <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
          Une carte par plat : sa photo, un titre, une phrase. Chaque changement s'affiche en direct dans l'aperçu ;
          sauvegardez pour publier.
        </p>
      </div>
      <span
        class="app-badge shrink-0 tabular-nums"
        :class="hasEnoughCards ? 'app-badge--success' : 'app-badge--progress'"
        :title="`${config.min_cards} cartes minimum`"
      >
        {{ cards.length }} carte{{ cards.length > 1 ? 's' : '' }}
      </span>
    </div>

    <section
      class="rounded-xl border border-[var(--app-line)] bg-[var(--app-surface)] p-3"
      aria-labelledby="service-cards-ai-title"
    >
      <div class="flex items-start gap-2.5">
        <span
          class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-[var(--app-ink)] text-[var(--app-bg)]"
          aria-hidden="true"
        >
          <UIcon name="i-lucide-sparkles" class="h-3.5 w-3.5" />
        </span>
        <div class="min-w-0 flex-1">
          <p id="service-cards-ai-title" class="text-sm font-semibold text-[var(--app-ink)]">Composer avec l'IA</p>
          <p class="mt-0.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">
            Regarde chaque photo, lit les menus photographiés et les avis, puis rédige {{ config.min_cards }} à
            {{ config.max_cards }} cartes avec la bonne photo pour chaque plat.
          </p>
        </div>
      </div>

      <div v-if="suggesting" class="mt-3 space-y-2" role="status" aria-live="polite">
        <div class="flex items-center gap-2 text-xs text-[var(--app-ink)]">
          <UIcon name="i-lucide-loader-circle" class="h-4 w-4 shrink-0 animate-spin" />
          <span>{{ suggestionProgressLabel }}</span>
        </div>
        <div class="relative h-[3px] overflow-hidden rounded-full bg-[var(--app-line)]" aria-hidden="true">
          <span
            class="service-cards-ai-progress-bar absolute inset-y-0 left-0 w-2/5 rounded-full bg-[var(--app-ink)] motion-reduce:w-full motion-reduce:animate-none motion-reduce:opacity-40"
          />
        </div>
        <p class="text-[10px] text-[var(--app-ink-soft)]">
          Une trentaine de secondes la première fois (les photos sont analysées une seule fois).
        </p>
      </div>
      <UiCallout v-else-if="suggestionError" variant="danger" class="mt-3">{{ suggestionError }}</UiCallout>
      <UiCallout v-else-if="!aiAvailable" variant="neutral" class="mt-3">
        Suggestion IA indisponible : aucune clé Groq n'est configurée sur le serveur. Les cartes restent éditables à la
        main.
      </UiCallout>
      <p v-else-if="analysisSummary" class="mt-3 text-[11px] leading-relaxed text-[var(--app-ink-soft)]">
        <UIcon name="i-lucide-scan-search" class="mr-1 inline-block h-3 w-3 align-[-2px]" />
        {{ analysisSummary }}
      </p>

      <button
        type="button"
        class="btn-primary mt-3 inline-flex w-full items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="suggesting || !aiAvailable"
        @click="emit('suggest')"
      >
        <UIcon name="i-lucide-sparkles" class="h-3.5 w-3.5" />
        {{ suggestButtonLabel }}
      </button>
      <p
        v-if="pendingLabelsCount > 0 && !suggesting && aiAvailable"
        class="mt-2 text-[10px] text-[var(--app-ink-soft)]"
      >
        {{ pendingLabelsCount }} photo{{ pendingLabelsCount > 1 ? 's' : '' }} pas encore analysée{{
          pendingLabelsCount > 1 ? 's' : ''
        }}
        : elles le seront au prochain lancement.
      </p>
    </section>

    <TransitionGroup
      v-if="displayedCards.length"
      ref="cardListRef"
      tag="ul"
      move-class="transition-transform duration-200 ease-out motion-reduce:transition-none"
      class="relative space-y-2"
      :aria-label="`Cartes de la section ${config.heading}`"
    >
      <li
        v-for="(card, index) in displayedCards"
        :key="card.key"
        :data-reorder-key="card.key"
        :class="[
          'rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-2',
          draggedCardKey === card.key ? 'drag-reorder-slot' : '',
        ]"
      >
        <div class="flex items-start gap-2">
          <button
            type="button"
            class="mt-1 cursor-grab touch-none text-[var(--app-ink-soft)] active:cursor-grabbing"
            :aria-label="`Déplacer la carte ${index + 1}`"
            @pointerdown="cardDrag.onGripPointerDown($event, card)"
          >
            <UIcon name="i-lucide-grip-vertical" class="h-4 w-4" />
          </button>

          <button
            type="button"
            class="group relative h-16 w-16 shrink-0 overflow-hidden rounded-lg border transition-colors"
            :class="
              openPhotoPickerCardKey === card.key
                ? 'border-[var(--app-ink)]'
                : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
            "
            :title="card.image ? 'Changer la photo' : 'Choisir une photo'"
            :aria-label="
              card.image ? `Changer la photo de la carte ${index + 1}` : `Choisir la photo de la carte ${index + 1}`
            "
            :aria-expanded="openPhotoPickerCardKey === card.key"
            @click="togglePhotoPicker(card.key)"
          >
            <img v-if="card.image" :src="card.image" alt="" class="h-full w-full object-cover" draggable="false" />
            <span
              v-else
              class="flex h-full w-full items-center justify-center bg-[var(--app-surface)] text-[var(--app-ink-soft)]"
            >
              <UIcon name="i-lucide-image-plus" class="h-5 w-5" />
            </span>
            <span
              v-if="card.image"
              class="drag-reorder-slot-label pointer-events-none absolute right-0.5 bottom-0.5 left-0.5 truncate rounded bg-[var(--app-overlay)] px-1 py-px text-center text-[8px] font-semibold text-white"
            >
              {{ PhotoLabels.label(photoKindForUrl(card.image)) }}
            </span>
          </button>

          <div class="min-w-0 flex-1 space-y-1.5">
            <input
              :value="card.title"
              type="text"
              class="input-field h-8 text-xs font-medium"
              placeholder="Nom du plat"
              maxlength="80"
              :aria-label="`Titre de la carte ${index + 1}`"
              @input="updateCard(card.key, { title: ($event.target as HTMLInputElement).value })"
            />
            <textarea
              :value="card.description"
              class="input-field min-h-[3.25rem] resize-none text-xs leading-relaxed"
              rows="2"
              maxlength="240"
              placeholder="Une phrase appétissante (optionnel)"
              :aria-label="`Description de la carte ${index + 1}`"
              @input="updateCard(card.key, { description: ($event.target as HTMLTextAreaElement).value })"
            />
            <div class="flex items-center justify-between gap-2 text-[10px] text-[var(--app-ink-soft)]">
              <span v-if="card.reason" class="flex min-w-0 items-center gap-1 italic" :title="card.reason">
                <UIcon name="i-lucide-sparkles" class="h-3 w-3 shrink-0" />
                <span class="truncate">{{ card.reason }}</span>
              </span>
              <span v-else />
              <span
                class="shrink-0 tabular-nums"
                :class="card.description.length > DESCRIPTION_SOFT_LIMIT ? 'text-[var(--app-accent-ink)]' : ''"
                :title="`${DESCRIPTION_SOFT_LIMIT} caractères conseillés`"
              >
                {{ card.description.length }}/{{ DESCRIPTION_SOFT_LIMIT }}
              </span>
            </div>
          </div>

          <button
            type="button"
            class="rounded-md p-1 text-[var(--app-ink-soft)] hover:text-[var(--app-red)]"
            aria-label="Retirer la carte"
            @click="removeCard(card.key)"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>

        <div v-if="openPhotoPickerCardKey === card.key" class="mt-2 border-t border-[var(--app-line)] pt-2">
          <p class="mb-1.5 text-[10px] font-semibold tracking-wide text-[var(--app-ink-soft)] uppercase">
            Photo de la carte
          </p>
          <div
            v-if="pickerPhotos.length"
            class="grid grid-cols-4 gap-1.5"
            role="listbox"
            aria-label="Photos du prospect"
          >
            <button
              v-for="photo in pickerPhotos"
              :key="photo.url"
              type="button"
              role="option"
              class="group relative aspect-square overflow-hidden rounded-lg border transition-colors"
              :class="
                photo.url === card.image
                  ? 'border-[var(--app-ink)] ring-2 ring-[var(--app-ink)]'
                  : 'border-[var(--app-line)] hover:border-[var(--app-ink-soft)]'
              "
              :aria-selected="photo.url === card.image"
              :title="photo.description || PhotoLabels.label(photo.kind)"
              @click="selectPhoto(card.key, photo.url)"
            >
              <img
                :src="photo.url"
                alt=""
                class="h-full w-full object-cover transition-opacity"
                :class="isUnfitForCard(photo) ? 'opacity-40 group-hover:opacity-70' : ''"
                draggable="false"
              />
              <span
                class="pointer-events-none absolute right-0.5 bottom-0.5 left-0.5 truncate rounded bg-[var(--app-overlay)] px-1 py-px text-center text-[8px] font-semibold text-white"
              >
                {{ PhotoLabels.label(photo.kind) }}
              </span>
              <span
                v-if="isUsedByAnotherCard(photo.url, card.key)"
                class="absolute top-0.5 right-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-[var(--app-overlay)] text-white"
                title="Déjà sur une autre carte"
              >
                <UIcon name="i-lucide-check" class="h-2.5 w-2.5" />
              </span>
            </button>
            <button
              type="button"
              role="option"
              class="flex aspect-square flex-col items-center justify-center gap-1 rounded-lg border border-dashed text-[10px] transition-colors"
              :class="
                card.image === ''
                  ? 'border-[var(--app-ink)] text-[var(--app-ink)]'
                  : 'border-[var(--app-line)] text-[var(--app-ink-soft)] hover:border-[var(--app-ink-soft)]'
              "
              :aria-selected="card.image === ''"
              title="Le site utilisera une photo de la galerie"
              @click="selectPhoto(card.key, '')"
            >
              <UIcon name="i-lucide-image-off" class="h-4 w-4" />
              Sans photo
            </button>
          </div>
          <p v-else class="text-[10px] text-[var(--app-ink-soft)]">Aucune photo exploitable pour ce prospect.</p>
          <p class="mt-1.5 text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
            Les plats sont en premier. Les photos estompées (camion, menu, flyer…) sont déconseillées sur une carte.
          </p>
        </div>
      </li>
    </TransitionGroup>

    <p v-else class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs text-[var(--app-ink-soft)]">
      Aucune carte pour l'instant : le site affiche celles générées automatiquement. Lancez l'IA ou ajoutez-en une.
    </p>

    <UiCallout v-if="hasCards && !hasEnoughCards" variant="warning">
      Au moins {{ config.min_cards }} cartes pour une section équilibrée : ajoutez-en {{ missingCardsCount }} ou lancez
      l'IA.
    </UiCallout>
    <UiCallout v-if="hasCards && !hasAllTitles" variant="warning">Chaque carte doit avoir un titre.</UiCallout>

    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        class="btn-secondary inline-flex flex-1 items-center justify-center gap-2 text-xs disabled:cursor-not-allowed disabled:opacity-50"
        :disabled="cards.length >= maximumCards"
        :title="cards.length >= maximumCards ? `${maximumCards} cartes maximum` : undefined"
        @click="addCard"
      >
        <UIcon name="i-lucide-plus" class="h-3.5 w-3.5" />
        Ajouter une carte
      </button>
      <button
        v-if="overrideActive"
        type="button"
        class="text-[11px] text-[var(--app-ink-soft)] underline underline-offset-2 transition-colors hover:text-[var(--app-ink)]"
        @click="emit('reset')"
      >
        Revenir aux cartes automatiques
      </button>
    </div>
    <p v-if="overrideActive && overrideSourceLabel" class="text-[10px] leading-relaxed text-[var(--app-ink-soft)]">
      <UIcon name="i-lucide-lock-keyhole" class="mr-1 inline-block h-3 w-3 align-[-2px]" />
      {{ overrideSourceLabel }}
    </p>
  </div>
</template>

<script lang="ts" setup>
import type { UseDragToReorderReturn } from '~/types/Composables'
import type { ServiceCardDraft, ServiceCardsEditorEmits, ServiceCardsEditorProps } from '~/types/ServiceCardsEditor'
import type {
  DemoSitePhotoLabel,
  DemoSiteServiceCardsAnalysis,
  DemoSiteServiceCardsConfig,
} from '~/services/demoSiteService'
import type { ComponentPublicInstance, ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useDragToReorder } from '~/composables/useDragToReorder'
import { PhotoLabels } from '~/utils/photoLabels'
import { ServiceCards } from '~/utils/serviceCards'

/** Description length the AI targets; longer texts are allowed but flagged. */
const DESCRIPTION_SOFT_LIMIT: number = 120

/** Cards the operator may add by hand, beyond what the AI composes. */
const MANUAL_CARDS_CEILING: number = 8

/** Progress messages shown while the AI works (it cannot stream, so the steps rotate on a timer). */
const SUGGESTION_PROGRESS_STEPS: string[] = [
  'Lecture des photos…',
  'Lecture des menus et des avis…',
  'Rédaction des cartes…',
  'Encore quelques secondes…',
]
const SUGGESTION_PROGRESS_STEP_MS: number = 5000

const props: ServiceCardsEditorProps = defineProps({
  cards: {
    type: Array as PropType<ServiceCardDraft[]>,
    required: true,
  },
  pool: {
    type: Array as PropType<DemoSitePhotoLabel[]>,
    required: true,
  },
  config: {
    type: Object as PropType<DemoSiteServiceCardsConfig>,
    required: true,
  },
  aiAvailable: {
    type: Boolean,
    default: false,
  },
  suggesting: {
    type: Boolean,
    default: false,
  },
  suggestionError: {
    type: String as PropType<string | null>,
    default: null,
  },
  analysis: {
    type: Object as PropType<DemoSiteServiceCardsAnalysis | null>,
    default: null,
  },
  overrideActive: {
    type: Boolean,
    default: false,
  },
  overrideSource: {
    type: String as PropType<string | null>,
    default: null,
  },
  labelsPending: {
    type: Number,
    default: 0,
  },
})

const emit: EmitFn<ServiceCardsEditorEmits> = defineEmits<ServiceCardsEditorEmits>()

const cardDrag: UseDragToReorderReturn<ServiceCardDraft> = useDragToReorder({
  axis: 'vertical',
  getContainer: cardListElement,
  getOrder: (): ServiceCardDraft[] => displayedCards.value,
  keyOf: (card: ServiceCardDraft): string => card.key,
  setDraftOrder: (order: ServiceCardDraft[] | null): void => {
    draftOrder.value = order
  },
  setDraggedKey: (key: string | null): void => {
    draggedCardKey.value = key
  },
  onCommit: (order: ServiceCardDraft[]): void => emit('update:cards', order),
  liftScale: 1.015,
})

const cardListRef: Ref<ComponentPublicInstance | null> = ref(null)
/** Key of the card being dragged, kept until its ghost has landed; null otherwise. */
const draggedCardKey: Ref<string | null> = ref(null)
const draftOrder: Ref<ServiceCardDraft[] | null> = ref(null)
const openPhotoPickerCardKey: Ref<string | null> = ref(null)
const suggestionProgressStep: Ref<number> = ref(0)
let suggestionProgressTimer: ReturnType<typeof setInterval> | null = null

const displayedCards: ComputedRef<ServiceCardDraft[]> = computed(
  (): ServiceCardDraft[] => draftOrder.value ?? props.cards,
)

const hasCards: ComputedRef<boolean> = computed((): boolean => props.cards.length > 0)

const pendingLabelsCount: ComputedRef<number> = computed((): number => props.labelsPending ?? 0)

const hasEnoughCards: ComputedRef<boolean> = computed((): boolean => props.cards.length >= props.config.min_cards)

const hasAllTitles: ComputedRef<boolean> = computed((): boolean =>
  props.cards.every((card: ServiceCardDraft): boolean => card.title.trim().length > 0),
)

const missingCardsCount: ComputedRef<number> = computed((): number =>
  Math.max(0, props.config.min_cards - props.cards.length),
)

const maximumCards: ComputedRef<number> = computed((): number => Math.max(props.config.max_cards, MANUAL_CARDS_CEILING))

/** Pool photos for the picker: dishes first (best appeal), then unanalysed ones, then the unfit ones. */
const pickerPhotos: ComputedRef<DemoSitePhotoLabel[]> = computed((): DemoSitePhotoLabel[] =>
  [...props.pool].sort((a: DemoSitePhotoLabel, b: DemoSitePhotoLabel): number => {
    const rankA: number = pickerPhotoSortRank(a)
    const rankB: number = pickerPhotoSortRank(b)
    if (rankA !== rankB) return rankA - rankB
    return b.appeal - a.appeal
  }),
)

const suggestionProgressLabel: ComputedRef<string> = computed(
  (): string => SUGGESTION_PROGRESS_STEPS[suggestionProgressStep.value] ?? SUGGESTION_PROGRESS_STEPS[0] ?? '',
)

const suggestButtonLabel: ComputedRef<string> = computed((): string => {
  if (props.suggesting) return 'Analyse en cours…'
  return hasCards.value ? 'Proposer à nouveau' : 'Analyser et proposer'
})

const analysisSummary: ComputedRef<string> = computed((): string => {
  const analysis: DemoSiteServiceCardsAnalysis | null | undefined = props.analysis
  if (!analysis) return ''
  const parts: string[] = [
    `${analysis.photos_total} photo${analysis.photos_total > 1 ? 's' : ''} analysée${analysis.photos_total > 1 ? 's' : ''}`,
    `${analysis.dish_photos} plat${analysis.dish_photos > 1 ? 's' : ''} en photo`,
  ]
  if (analysis.menu_boards > 0) {
    parts.push(
      `${analysis.menu_boards} menu${analysis.menu_boards > 1 ? 's' : ''} lu${analysis.menu_boards > 1 ? 's' : ''} (${analysis.menu_dishes} plat${analysis.menu_dishes > 1 ? 's' : ''})`,
    )
  }
  parts.push(`${analysis.reviews_used} avis`)
  return parts.join(' · ')
})

const overrideSourceLabel: ComputedRef<string> = computed((): string => {
  switch (props.overrideSource) {
    case 'ai_auto':
      return "Cartes composées par l'IA à la création du site, conservées à chaque régénération."
    case 'ai':
      return "Cartes proposées par l'IA, conservées à chaque régénération."
    case 'manual':
      return 'Cartes personnalisées, conservées à chaque régénération.'
    default:
      return ''
  }
})

/**
 * The rendered card list, which is the offsetParent of its rows.
 * @returns The `<ul>` element, or null before it is rendered.
 */
function cardListElement(): HTMLElement | null {
  const element: unknown = cardListRef.value?.$el
  return element instanceof HTMLElement ? element : null
}

/**
 * Sort bucket of a pool photo in the picker.
 * @param photo - A labelled pool photo.
 * @returns 0 for a dish or drink, 1 when not analysed yet, 2 when unfit for a card.
 */
function pickerPhotoSortRank(photo: DemoSitePhotoLabel): number {
  if (photo.card_worthy) return 0
  return photo.kind === 'unknown' ? 1 : 2
}

/**
 * Whether a pool photo is known to be wrong on a card (truck, menu board, flyer…).
 * @param photo - A labelled pool photo.
 * @returns True for an analysed photo that is neither a dish nor a drink.
 */
function isUnfitForCard(photo: DemoSitePhotoLabel): boolean {
  return !photo.card_worthy && photo.kind !== 'unknown'
}

/**
 * Vision kind of a pool photo by URL.
 * @param url - Photo URL.
 * @returns The kind, or `unknown` outside the pool.
 */
function photoKindForUrl(url: string): string {
  return props.pool.find((photo: DemoSitePhotoLabel): boolean => photo.url === url)?.kind ?? 'unknown'
}

/**
 * Whether a photo already illustrates another card than the given one.
 * @param url - Photo URL.
 * @param cardKey - The card being edited.
 * @returns True when another card carries this photo.
 */
function isUsedByAnotherCard(url: string, cardKey: string): boolean {
  return props.cards.some((card: ServiceCardDraft): boolean => card.key !== cardKey && card.image === url)
}

/**
 * Open or close the photo picker of a card (one open at a time).
 * @param cardKey - The card's key.
 */
function togglePhotoPicker(cardKey: string): void {
  openPhotoPickerCardKey.value = openPhotoPickerCardKey.value === cardKey ? null : cardKey
}

/**
 * Emit the list with one card patched.
 * @param cardKey - The card's key.
 * @param patch - Fields to change.
 */
function updateCard(cardKey: string, patch: Partial<Pick<ServiceCardDraft, 'title' | 'description' | 'image'>>): void {
  emit(
    'update:cards',
    props.cards.map(
      (card: ServiceCardDraft): ServiceCardDraft => (card.key === cardKey ? { ...card, ...patch } : card),
    ),
  )
}

/**
 * Set (or clear) a card's photo and close the picker.
 * @param cardKey - The card's key.
 * @param url - Photo URL, or '' for no photo.
 */
function selectPhoto(cardKey: string, url: string): void {
  updateCard(cardKey, { image: url })
  openPhotoPickerCardKey.value = null
}

/**
 * Remove a card.
 * @param cardKey - The card's key.
 */
function removeCard(cardKey: string): void {
  if (openPhotoPickerCardKey.value === cardKey) openPhotoPickerCardKey.value = null
  emit(
    'update:cards',
    props.cards.filter((card: ServiceCardDraft): boolean => card.key !== cardKey),
  )
}

/**
 * Append an empty card and open its photo picker.
 */
function addCard(): void {
  if (props.cards.length >= maximumCards.value) return
  const card: ServiceCardDraft = { key: ServiceCards.newKey(), title: '', description: '', image: '', reason: '' }
  emit('update:cards', [...props.cards, card])
  openPhotoPickerCardKey.value = card.key
}

/**
 * Stop rotating the progress messages.
 */
function stopSuggestionProgress(): void {
  if (suggestionProgressTimer !== null) {
    clearInterval(suggestionProgressTimer)
    suggestionProgressTimer = null
  }
}

watch(
  (): boolean => props.suggesting ?? false,
  (active: boolean): void => {
    stopSuggestionProgress()
    suggestionProgressStep.value = 0
    if (!active) return
    suggestionProgressTimer = setInterval((): void => {
      suggestionProgressStep.value = Math.min(suggestionProgressStep.value + 1, SUGGESTION_PROGRESS_STEPS.length - 1)
    }, SUGGESTION_PROGRESS_STEP_MS)
  },
)

onBeforeUnmount((): void => {
  stopSuggestionProgress()
  cardDrag.cancelDrag()
})
</script>

<style scoped>
.service-cards-ai-progress-bar {
  animation: service-cards-ai-progress 1.6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes service-cards-ai-progress {
  from {
    transform: translateX(-100%);
  }
  to {
    transform: translateX(260%);
  }
}
</style>
