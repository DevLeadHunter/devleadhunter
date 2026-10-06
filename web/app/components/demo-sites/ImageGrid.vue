<template>
  <div class="space-y-4">
    <div v-if="!isHeadingHidden">
      <p class="app-label">Images du site</p>
      <p class="mt-1 text-xs leading-relaxed text-[var(--app-ink-soft)]">
        Maintenez une photo puis glissez-la pour la déplacer. La première est l’en-tête, la deuxième « à propos », le
        reste la galerie.
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
          'group relative aspect-[4/3] cursor-grab touch-pan-y overflow-hidden rounded-xl border bg-[var(--app-bg)] transition-transform duration-150 select-none [-webkit-touch-callout:none] active:cursor-grabbing motion-reduce:transition-none',
          i === 0 ? 'border-[var(--app-accent)] ring-2 ring-[var(--app-accent)]/30' : 'border-[var(--app-line)]',
          draggedUrl === url ? 'drag-reorder-slot' : '',
          pressedUrl === url ? 'scale-[0.97]' : '',
        ]"
        @pointerdown="onTilePointerDown($event, url)"
        @pointermove="onTilePointerMove"
        @pointerup="onTilePointerEnd"
        @pointercancel="onTilePointerEnd"
        @touchmove="onTileTouchMove"
        @touchend="onTileTouchEnd"
        @touchcancel="onTileTouchEnd"
        @contextmenu.prevent
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
import type { ImageGridLongPress, ImageSlotsEmits, ImageSlotsProps } from '~/types/ImageSlots'
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

/** How long a finger rests on a photo before it lifts: a quicker swipe scrolls the sheet instead. */
const LONG_PRESS_DELAY_MS: number = 200

/** Travel allowed during the hold; past it the gesture is a scroll and the photo stays put. */
const LONG_PRESS_MOVE_TOLERANCE_PX: number = 8

const placementGridRef: Ref<ComponentPublicInstance | null> = ref(null)
const draggedUrl: Ref<string | null> = ref(null)
const draftOrder: Ref<string[] | null> = ref(null)
const lightboxIndex: Ref<number | null> = ref(null)
const pressedUrl: Ref<string | null> = ref(null)
let longPress: ImageGridLongPress | null = null
let isTileLifted: boolean = false

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
 * A press on a tile: a mouse or a pen picks the photo up at once, a finger has to rest on it first.
 * @param event - The pointer pressed on the tile.
 * @param url - The photo of the tile.
 */
function onTilePointerDown(event: PointerEvent, url: string): void {
  if (!event.isTrusted) return
  if (event.pointerType !== 'touch') {
    placementDrag.onGripPointerDown(event, url)
    return
  }
  if (!event.isPrimary || !(event.currentTarget instanceof HTMLElement)) return
  cancelLongPress()
  longPress = {
    url,
    tile: event.currentTarget,
    pointerId: event.pointerId,
    startClientX: event.clientX,
    startClientY: event.clientY,
    lastClientX: event.clientX,
    lastClientY: event.clientY,
    timer: setTimeout(liftPressedPhoto, LONG_PRESS_DELAY_MS),
  }
  pressedUrl.value = url
}

/**
 * Follow the resting finger: if it travels before the photo lifts, the gesture is a scroll.
 * @param event - The pointer moving over the tile.
 */
function onTilePointerMove(event: PointerEvent): void {
  if (!longPress || event.pointerId !== longPress.pointerId) return
  longPress.lastClientX = event.clientX
  longPress.lastClientY = event.clientY
  const travel: number = Math.hypot(event.clientX - longPress.startClientX, event.clientY - longPress.startClientY)
  if (travel > LONG_PRESS_MOVE_TOLERANCE_PX) cancelLongPress()
}

/**
 * The finger left or the browser took the gesture over for a scroll before the photo lifted.
 * @param event - The pointer lifted or cancelled.
 */
function onTilePointerEnd(event: PointerEvent): void {
  if (longPress && event.pointerId === longPress.pointerId) cancelLongPress()
}

/**
 * Forget the resting finger, without lifting anything.
 */
function cancelLongPress(): void {
  if (longPress) clearTimeout(longPress.timer)
  longPress = null
  pressedUrl.value = null
}

/**
 * The finger rested long enough: hand the press to the reorder engine, as if the tile had just been grabbed where the
 * finger is now, so the next moves drag the photo instead of scrolling the sheet.
 */
function liftPressedPhoto(): void {
  const press: ImageGridLongPress | null = longPress
  longPress = null
  pressedUrl.value = null
  if (!press) return
  isTileLifted = true
  /**
   * Start the drag from the tile itself, which the engine reads as the grabbed grip.
   * @param event - The press replayed on the tile.
   */
  const grabTile: (event: PointerEvent) => void = (event: PointerEvent): void => {
    placementDrag.onGripPointerDown(event, press.url)
  }
  press.tile.addEventListener('pointerdown', grabTile, { once: true })
  press.tile.dispatchEvent(
    new PointerEvent('pointerdown', {
      pointerId: press.pointerId,
      pointerType: 'touch',
      isPrimary: true,
      button: 0,
      buttons: 1,
      clientX: press.lastClientX,
      clientY: press.lastClientY,
      cancelable: true,
    }),
  )
}

/**
 * Once a photo is lifted, the finger drags it: the sheet must not scroll under it.
 * @param event - The finger moving.
 */
function onTileTouchMove(event: TouchEvent): void {
  if (isTileLifted && event.cancelable) event.preventDefault()
}

/**
 * The finger left the screen: the next touch starts again with a scroll or a hold.
 */
function onTileTouchEnd(): void {
  isTileLifted = false
  cancelLongPress()
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
  cancelLongPress()
  placementDrag.cancelDrag()
})
</script>
