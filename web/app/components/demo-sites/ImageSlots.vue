<template>
  <div class="space-y-4">
    <div>
      <p class="app-label">Images du site</p>
      <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        La 1ʳᵉ photo devient l'en-tête, la 2ᵉ la section « à propos », le reste la galerie. Chaque changement s'affiche
        en direct dans l'aperçu ; sauvegardez pour publier.
      </p>
    </div>

    <TransitionGroup
      v-if="displayedOrder.length"
      ref="placementListRef"
      tag="ul"
      move-class="transition-transform duration-200 ease-out motion-reduce:transition-none"
      class="relative space-y-2"
      aria-label="Photos placées sur le site"
    >
      <li
        v-for="(url, i) in displayedOrder"
        :key="url"
        :data-reorder-key="url"
        :class="[
          'flex items-center gap-2 rounded-xl border border-[var(--app-line)] bg-[var(--app-bg)] p-2',
          draggedUrl === url ? 'drag-reorder-slot' : '',
        ]"
      >
        <button
          type="button"
          class="cursor-grab touch-none text-[var(--app-ink-soft)] active:cursor-grabbing"
          aria-label="Déplacer la photo"
          @pointerdown="placementDrag.onGripPointerDown($event, url)"
        >
          <UIcon name="i-lucide-grip-vertical" class="h-4 w-4" />
        </button>

        <button
          type="button"
          class="shrink-0 cursor-zoom-in overflow-hidden rounded-lg"
          title="Voir en grand"
          :aria-label="`Voir la photo ${i + 1} en grand`"
          @click="openLightbox(url)"
        >
          <img :src="url" :alt="`Photo ${i + 1}`" class="h-12 w-16 object-cover" draggable="false" />
        </button>

        <span
          :class="[
            'drag-reorder-slot-label rounded-full px-1.5 py-0.5 text-[9px] font-bold uppercase',
            slotBadgeClass(i),
          ]"
        >
          {{ slotLabel(i) }}
        </span>

        <div class="ml-auto flex items-center">
          <button
            type="button"
            class="rounded-md p-1 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Mettre en photo principale"
            :disabled="i === 0"
            @click="moveToFront(i)"
          >
            <UIcon name="i-lucide-chevrons-up" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Monter"
            :disabled="i === 0"
            @click="move(i, i - 1)"
          >
            <UIcon name="i-lucide-arrow-up" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1 text-[var(--app-ink-soft)] hover:text-[var(--app-ink)] disabled:opacity-30"
            aria-label="Descendre"
            :disabled="i === displayedOrder.length - 1"
            @click="move(i, i + 1)"
          >
            <UIcon name="i-lucide-arrow-down" class="h-4 w-4" />
          </button>
          <button
            type="button"
            class="rounded-md p-1 text-[var(--app-ink-soft)] hover:text-[var(--app-red)]"
            aria-label="Retirer du site"
            @click="removeAt(i)"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
      </li>
    </TransitionGroup>

    <p v-else class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs text-[var(--app-ink-soft)]">
      Aucune photo placée : le site utilise ses images par défaut. Ajoutez-en depuis « Non utilisées ».
    </p>

    <div v-if="unused.length" class="space-y-2 border-t border-[var(--app-line)] pt-4">
      <p class="text-xs font-semibold text-[var(--app-ink-soft)]">Non utilisées ({{ unused.length }})</p>
      <div class="flex flex-wrap gap-2">
        <div
          v-for="url in unused"
          :key="url"
          class="group relative overflow-hidden rounded-lg border border-[var(--app-line)]"
        >
          <button type="button" class="block" title="Ajouter au site" @click="add(url)">
            <img
              :src="url"
              alt="Photo non utilisée"
              class="h-14 w-20 object-cover opacity-70 transition-opacity group-hover:opacity-100"
              draggable="false"
            />
            <span
              class="absolute inset-0 flex items-center justify-center bg-black/40 text-white opacity-0 transition-opacity group-hover:opacity-100"
            >
              <UIcon name="i-lucide-plus" class="h-5 w-5" />
            </span>
          </button>
          <button
            type="button"
            class="absolute top-0.5 right-0.5 flex h-5 w-5 cursor-zoom-in items-center justify-center rounded bg-[var(--app-overlay)] text-white opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100"
            title="Voir en grand"
            aria-label="Voir la photo en grand"
            @click.stop="openLightbox(url)"
          >
            <UIcon name="i-lucide-maximize-2" class="h-3 w-3" />
          </button>
        </div>
      </div>
    </div>

    <UiImageLightbox v-model="lightboxIndex" :photos="lightboxPhotos" />
  </div>
</template>

<script lang="ts" setup>
import type { UseDragToReorderReturn } from '~/types/Composables'
import type { ImageSlotsEmits, ImageSlotsProps } from '~/types/ImageSlots'
import type { ComponentPublicInstance, ComputedRef, EmitFn, PropType, Ref } from 'vue'
import { computed, onBeforeUnmount, ref } from 'vue'
import { useDragToReorder } from '~/composables/useDragToReorder'

/**
 * Controlled editor placing the prospect's photos into the site's hero / about / gallery slots.
 * Every gesture emits the new order immediately — the parent shows it live in the preview and
 * owns the save (no local apply step).
 */
const props: ImageSlotsProps = defineProps({
  pool: {
    type: Array as PropType<string[]>,
    required: true,
  },
  order: {
    type: Array as PropType<string[]>,
    required: true,
  },
})

const emit: EmitFn<ImageSlotsEmits> = defineEmits<ImageSlotsEmits>()

const placementDrag: UseDragToReorderReturn<string> = useDragToReorder({
  axis: 'vertical',
  getContainer: placementListElement,
  getOrder: (): string[] => displayedOrder.value,
  keyOf: (url: string): string => url,
  setDraftOrder: (order: string[] | null): void => {
    draftOrder.value = order
  },
  setDraggedKey: (url: string | null): void => {
    draggedUrl.value = url
  },
  onCommit: (order: string[]): void => emit('update:order', order),
  liftScale: 1.015,
})

const placementListRef: Ref<ComponentPublicInstance | null> = ref(null)

/** URL of the photo being dragged, kept until its ghost has landed; null otherwise. */
const draggedUrl: Ref<string | null> = ref(null)

const draftOrder: Ref<string[] | null> = ref(null)
/** Index of the photo shown fullscreen in the lightbox, or null when closed. */
const lightboxIndex: Ref<number | null> = ref(null)

const displayedOrder: ComputedRef<string[]> = computed((): string[] => draftOrder.value ?? props.order)

const unused: ComputedRef<string[]> = computed((): string[] =>
  props.pool.filter((url: string): boolean => !props.order.includes(url)),
)

/** Every photo the lightbox can page through: the placed ones in site order, then the unused ones. */
const lightboxPhotos: ComputedRef<string[]> = computed((): string[] => [...displayedOrder.value, ...unused.value])

/**
 * The rendered placement list, which is the offsetParent of its rows.
 * @returns The `<ul>` element, or null before it is rendered.
 */
function placementListElement(): HTMLElement | null {
  const element: unknown = placementListRef.value?.$el
  return element instanceof HTMLElement ? element : null
}

/**
 * Destination label for a photo at a given placement index.
 * @param index - Position in the placement list.
 */
function slotLabel(index: number): string {
  if (index === 0) return 'Principale'
  if (index === 1) return 'À propos'
  return `Galerie ${index - 1}`
}

/**
 * Badge colour for a placement slot — the hero slot is highlighted, the rest are muted.
 * @param index - Position in the placement list.
 */
function slotBadgeClass(index: number): string {
  if (index === 0) return 'bg-[var(--app-accent-soft)] text-[var(--app-accent-ink)]'
  return 'bg-[var(--app-line)] text-[var(--app-ink-soft)]'
}

/**
 * Move a placed photo from one index to another, keeping the rest in order.
 * @param from - Current index.
 * @param to - Target index.
 */
function move(from: number, to: number): void {
  if (to < 0 || to >= props.order.length) return
  const next: string[] = [...props.order]
  const moved: string | undefined = next.splice(from, 1)[0]
  if (moved === undefined) return
  next.splice(to, 0, moved)
  emit('update:order', next)
}

/**
 * Promote a placed photo to the hero slot (index 0).
 * @param index - Current index of the photo.
 */
function moveToFront(index: number): void {
  move(index, 0)
}

/**
 * Remove a photo from the site (it returns to the "unused" pool).
 * @param index - Index of the photo to drop.
 */
function removeAt(index: number): void {
  emit(
    'update:order',
    props.order.filter((_: string, i: number): boolean => i !== index),
  )
}

/**
 * Add an unused photo to the end of the placement (gallery).
 * @param url - Photo URL to add.
 */
function add(url: string): void {
  if (props.order.includes(url)) return
  emit('update:order', [...props.order, url])
}

/**
 * Open the fullscreen lightbox on a photo.
 * @param url - Photo URL to show.
 */
function openLightbox(url: string): void {
  const index: number = lightboxPhotos.value.indexOf(url)
  lightboxIndex.value = index >= 0 ? index : null
}

onBeforeUnmount((): void => {
  placementDrag.cancelDrag()
})
</script>
