<template>
  <div ref="paneElement" class="relative h-full w-full overflow-hidden bg-[var(--app-surface-2)]">
    <iframe
      v-if="frameUrl"
      ref="frameElement"
      :src="frameUrl"
      :class="[
        'absolute origin-top-left border-0 bg-white shadow-[var(--app-shadow-soft)] ring-1 ring-black/10',
        device === 'mobile' ? 'rounded-[28px]' : 'rounded-lg',
      ]"
      :style="frameStyle"
      title="Le site, en direct"
      @load="endFrameLoad"
    />
    <Transition name="preview-veil">
      <div
        v-if="isLoading"
        class="absolute inset-0 flex flex-col items-center justify-center gap-3.5 bg-[var(--app-surface)]"
      >
        <div class="loader-smooth"></div>
        <span class="text-xs text-[var(--app-ink-soft)]">Chargement du site…</span>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { DemoSiteServiceCard, DemoSiteTheme } from '~/services/demoSiteService'
import type { AtelierPreviewProps, AtelierPreviewScreenSize } from '~/types/AtelierPreview'
import type { TemplatePreviewDevice } from '~/types/TemplatePicker'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

/** Real screens, at scale 1: a laptop and a phone. The frame keeps their ratio whatever the pane. */
const FRAME_SIZES: Record<TemplatePreviewDevice, AtelierPreviewScreenSize> = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
}

/** Air kept around the frame, so it reads as a device and not as a cut-out. */
const FRAME_INSET_PX: number = 16

/** An unreachable demo host never fires `load`: past this delay the veil lifts anyway. */
const FRAME_LOAD_TIMEOUT_MS: number = 8_000

/** Pause after the last edit before it is pushed into the site, so typing a colour does not flood it. */
const OVERRIDES_DEBOUNCE_MS: number = 200

/**
 * The published site in a real screen (laptop or phone) scaled to fit the pane, scrolling inside, redrawn live
 * with the unsaved edits (template, colours, photo order, cards) through the demo host's `_edit=1` mode.
 */
const props: AtelierPreviewProps = defineProps({
  siteUrl: {
    type: String,
    required: true,
  },
  device: {
    type: String as PropType<TemplatePreviewDevice>,
    default: 'mobile',
  },
  templateId: {
    type: String,
    required: true,
  },
  previewTheme: {
    type: Object as PropType<DemoSiteTheme | null>,
    default: null,
  },
  previewPhotos: {
    type: Array as PropType<string[] | null>,
    default: null,
  },
  previewServices: {
    type: Array as PropType<DemoSiteServiceCard[] | null>,
    default: null,
  },
  reloadNonce: {
    type: Number,
    default: 0,
  },
})

const paneElement: Ref<HTMLElement | null> = ref(null)
const frameElement: Ref<HTMLIFrameElement | null> = ref(null)
const paneWidth: Ref<number> = ref(0)
const paneHeight: Ref<number> = ref(0)
const isLoading: Ref<boolean> = ref(true)
let resizeObserver: ResizeObserver | null = null
let messageTimer: ReturnType<typeof setTimeout> | null = null
let frameLoadTimeoutTimer: ReturnType<typeof setTimeout> | null = null

const frameUrl: ComputedRef<string> = computed((): string => {
  const separator: string = props.siteUrl.includes('?') ? '&' : '?'
  const nonce: string = props.reloadNonce ? `&_r=${props.reloadNonce}` : ''
  return `${props.siteUrl}${separator}_edit=1${nonce}`
})

/** Scale of the frame so the whole screen fits the pane, whichever side is tight. */
const frameScale: ComputedRef<number> = computed((): number => {
  if (paneWidth.value === 0 || paneHeight.value === 0) return 1
  const frame: AtelierPreviewScreenSize = FRAME_SIZES[props.device ?? 'mobile']
  const widthScale: number = (paneWidth.value - FRAME_INSET_PX * 2) / frame.width
  const heightScale: number = (paneHeight.value - FRAME_INSET_PX * 2) / frame.height
  return Math.min(1, widthScale, heightScale)
})

/** The frame at its real size, scaled and centred in the pane. */
const frameStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const scale: number = frameScale.value
  const frame: AtelierPreviewScreenSize = FRAME_SIZES[props.device ?? 'mobile']
  return {
    width: `${frame.width}px`,
    height: `${frame.height}px`,
    transform: `scale(${scale})`,
    left: `calc(50% - ${(frame.width * scale) / 2}px)`,
    top: `calc(50% - ${(frame.height * scale) / 2}px)`,
  }
})

/**
 * Push the unsaved edits into the site, which repaints at once.
 */
function postOverrides(): void {
  const frame: HTMLIFrameElement | null = frameElement.value
  if (!frame?.contentWindow) return
  let origin: string
  try {
    origin = new URL(props.siteUrl).origin
  } catch {
    return
  }
  frame.contentWindow.postMessage(
    {
      type: 'dlh:preview',
      templateId: props.templateId,
      palette: props.previewTheme ? { ...props.previewTheme } : null,
      photos: props.previewPhotos ? [...props.previewPhotos] : null,
      services: props.previewServices
        ? props.previewServices.map((card: DemoSiteServiceCard): DemoSiteServiceCard => ({ ...card }))
        : null,
    },
    origin,
  )
}

/**
 * Debounced {@link postOverrides}, so typing a colour or dragging a photo does not flood the site.
 */
function scheduleOverrides(): void {
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(postOverrides, OVERRIDES_DEBOUNCE_MS)
}

/**
 * Cover the frame while the site loads, for a bounded time.
 */
function beginFrameLoad(): void {
  isLoading.value = true
  if (frameLoadTimeoutTimer) clearTimeout(frameLoadTimeoutTimer)
  frameLoadTimeoutTimer = setTimeout((): void => {
    isLoading.value = false
  }, FRAME_LOAD_TIMEOUT_MS)
}

/**
 * Lift the veil once the site is loaded and send it the unsaved edits again: a fresh load starts from the
 * published site, so edits made before it (or while the frame was away) would be lost otherwise.
 */
function endFrameLoad(): void {
  if (frameLoadTimeoutTimer) clearTimeout(frameLoadTimeoutTimer)
  isLoading.value = false
  postOverrides()
}

watch(
  [
    (): string => props.templateId,
    (): DemoSiteTheme | null => props.previewTheme ?? null,
    (): string[] | null => props.previewPhotos ?? null,
    (): DemoSiteServiceCard[] | null => props.previewServices ?? null,
  ],
  scheduleOverrides,
  { deep: true },
)

watch(frameUrl, beginFrameLoad, { immediate: true })

watch(paneElement, (element: HTMLElement | null): void => {
  resizeObserver?.disconnect()
  resizeObserver = null
  if (!element) return
  resizeObserver = new ResizeObserver((entries: ResizeObserverEntry[]): void => {
    const entry: ResizeObserverEntry | undefined = entries[0]
    if (!entry) return
    paneWidth.value = entry.contentRect.width
    paneHeight.value = entry.contentRect.height
  })
  resizeObserver.observe(element)
})

onBeforeUnmount((): void => {
  resizeObserver?.disconnect()
  if (messageTimer) clearTimeout(messageTimer)
  if (frameLoadTimeoutTimer) clearTimeout(frameLoadTimeoutTimer)
})
</script>

<style scoped>
.preview-veil-leave-active {
  transition: opacity 0.2s ease;
}
.preview-veil-leave-to {
  opacity: 0;
}
@media (prefers-reduced-motion: reduce) {
  .preview-veil-leave-active {
    transition: none;
  }
}
</style>
