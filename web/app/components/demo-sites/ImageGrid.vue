<template>
  <div class="space-y-4">
    <div v-if="!isHeadingHidden">
      <p class="app-label">Images du site</p>
      <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        Glissez une photo pour la déplacer. La première est l’en-tête, la deuxième « à propos », le reste la galerie.
      </p>
    </div>

    <TransitionGroup
      v-if="displayedOrder.length"
      ref="placementGridRef"
      tag="ul"
      move-class="transition-transform duration-200 ease-out motion-reduce:transition-none"
      class="relative grid grid-cols-2 gap-3 sm:grid-cols-3"
      aria-label="Photos placées sur le site"
    >
      <li
        v-for="(url, i) in displayedOrder"
        :key="url"
        :data-reorder-key="url"
        :class="[
          'group relative aspect-[4/3] cursor-grab touch-none overflow-hidden rounded-xl border bg-[var(--app-bg)] select-none [-webkit-touch-callout:none] active:cursor-grabbing',
          i === 0 ? 'border-[var(--app-accent)] ring-2 ring-[var(--app-accent)]/30' : 'border-[var(--app-line)]',
          draggedUrl === url ? 'drag-reorder-slot' : '',
        ]"
        @pointerdown="placementDrag.onGripPointerDown($event, url)"
      >
        <img :src="url" :alt="`Photo ${i + 1}`" class="h-full w-full object-cover" draggable="false" />
        <span
          :class="[
            'drag-reorder-slot-label absolute top-2 left-2 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase shadow-sm',
            i === 0 ? 'bg-[var(--app-accent)] text-[#1b1508]' : 'bg-[var(--app-surface)] text-[var(--app-ink)]',
          ]"
        >
          {{ slotLabel(i) }}
        </span>
        <div class="absolute top-1.5 right-1.5 flex gap-2">
          <button
            type="button"
            class="relative flex h-8 w-8 cursor-zoom-in items-center justify-center rounded-full bg-[var(--app-overlay)] text-white before:absolute before:-inset-1 before:content-['']"
            title="Voir en grand"
            :aria-label="`Voir la photo ${i + 1} en grand`"
            @pointerdown.stop
            @click="openLightbox(url)"
          >
            <UIcon name="i-lucide-maximize-2" class="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            class="relative flex h-8 w-8 cursor-pointer items-center justify-center rounded-full bg-[var(--app-overlay)] text-white before:absolute before:-inset-1 before:content-['']"
            title="Retirer du site"
            :aria-label="`Retirer la photo ${i + 1} du site`"
            @pointerdown.stop
            @click="removeAt(i)"
          >
            <UIcon name="i-lucide-x" class="h-4 w-4" />
          </button>
        </div>
        <button
          v-if="i !== 0"
          type="button"
          class="absolute right-1.5 bottom-1.5 flex h-8 cursor-pointer items-center gap-1 rounded-full bg-[var(--app-overlay)] px-2.5 text-[11px] font-medium text-white before:absolute before:-inset-1 before:content-['']"
          :aria-label="`Mettre la photo ${i + 1} en photo principale`"
          @pointerdown.stop
          @click="moveToFront(i)"
        >
          <UIcon name="i-lucide-star" class="h-3.5 w-3.5" />
          Principale
        </button>
        <span
          class="absolute bottom-1.5 left-1.5 flex h-8 w-8 items-center justify-center rounded-full bg-[var(--app-overlay)] text-white"
          aria-hidden="true"
        >
          <UIcon name="i-lucide-grip-horizontal" class="h-4 w-4" />
        </span>
      </li>
    </TransitionGroup>

    <p v-else class="rounded-xl border border-dashed border-[var(--app-line)] p-4 text-xs text-[var(--app-ink-soft)]">
      Aucune photo placée : le site utilise ses images par défaut. Ajoutez-en depuis « Non utilisées ».
    </p>

    <div v-if="unused.length" class="space-y-2 border-t border-[var(--app-line)] pt-4">
      <p class="text-xs font-semibold text-[var(--app-ink-soft)]">Non utilisées ({{ unused.length }})</p>
      <div class="grid grid-cols-4 gap-2 sm:grid-cols-6">
        <button
          v-for="url in unused"
          :key="url"
          type="button"
          class="group relative aspect-[4/3] cursor-pointer overflow-hidden rounded-lg border border-[var(--app-line)] [-webkit-touch-callout:none]"
          title="Ajouter au site"
          aria-label="Ajouter la photo au site, en fin de galerie"
          @click="add(url)"
        >
          <img :src="url" alt="" class="h-full w-full object-cover opacity-60" draggable="false" />
          <span class="absolute inset-0 flex items-center justify-center bg-[var(--app-overlay)] text-white">
            <UIcon name="i-lucide-plus" class="h-5 w-5" />
          </span>
        </button>
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
 * The prospect's photos as large tiles one drags with a finger: the first is the hero, the second « à propos »,
 * the rest the gallery. Every gesture emits the new order at once; the parent shows it live and owns the save.
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
  isHeadingHidden: {
    type: Boolean,
    default: false,
  },
})

const emit: EmitFn<ImageSlotsEmits> = defineEmits<ImageSlotsEmits>()

const placementGridRef: Ref<ComponentPublicInstance | null> = ref(null)
const draggedUrl: Ref<string | null> = ref(null)
const draftOrder: Ref<string[] | null> = ref(null)
const lightboxIndex: Ref<number | null> = ref(null)

const placementDrag: UseDragToReorderReturn<string> = useDragToReorder({
  axis: 'grid',
  getContainer: placementGridElement,
  getOrder: (): string[] => displayedOrder.value,
  keyOf: (url: string): string => url,
  setDraftOrder: (order: string[] | null): void => {
    draftOrder.value = order
  },
  setDraggedKey: (url: string | null): void => {
    draggedUrl.value = url
  },
  onCommit: (order: string[]): void => emit('update:order', order),
  liftScale: 1.04,
})

const displayedOrder: ComputedRef<string[]> = computed((): string[] => draftOrder.value ?? props.order)

const unused: ComputedRef<string[]> = computed((): string[] =>
  props.pool.filter((url: string): boolean => !props.order.includes(url)),
)

const lightboxPhotos: ComputedRef<string[]> = computed((): string[] => [...displayedOrder.value, ...unused.value])

/**
 * The rendered grid, which is the offsetParent of its tiles.
 * @returns The `<ul>` element, or null before it is rendered.
 */
function placementGridElement(): HTMLElement | null {
  const element: unknown = placementGridRef.value?.$el
  return element instanceof HTMLElement ? element : null
}

/**
 * Destination label for a photo at a given placement index.
 * @param index - Position in the grid.
 * @returns « Principale », « À propos » or « Galerie n ».
 */
function slotLabel(index: number): string {
  if (index === 0) return 'Principale'
  if (index === 1) return 'À propos'
  return `Galerie ${index - 1}`
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
 * Promote a placed photo to the hero slot.
 * @param index - Current index of the photo.
 */
function moveToFront(index: number): void {
  move(index, 0)
}

/**
 * Remove a photo from the site; it goes back to the unused ones.
 * @param index - Index of the photo to drop.
 */
function removeAt(index: number): void {
  emit(
    'update:order',
    props.order.filter((_: string, i: number): boolean => i !== index),
  )
}

/**
 * Add an unused photo at the end of the gallery.
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
