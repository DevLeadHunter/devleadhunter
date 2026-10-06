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
      title="La page, en direct"
      @load="endFrameLoad"
    />
    <Transition name="preview-veil">
      <div
        v-if="isLoading"
        class="absolute inset-0 flex flex-col items-center justify-center gap-3.5 bg-[var(--app-surface)]"
      >
        <div class="loader-smooth"></div>
        <span class="text-xs text-[var(--app-ink-soft)]">Chargement de la page…</span>
      </div>
    </Transition>
  </div>
</template>

<script lang="ts" setup>
import type { ComputedRef, PropType, Ref } from 'vue'
import type { AtelierDevicePreviewProps, AtelierDevicePreviewScreenSize } from '~/types/AtelierDevicePreview'
import type { TemplatePreviewDevice } from '~/types/TemplatePicker'
import { computed, onBeforeUnmount, ref, watch } from 'vue'

/** Real screens, at scale 1: a laptop and a phone. The frame keeps their ratio whatever the pane. */
const FRAME_SIZES: Record<TemplatePreviewDevice, AtelierDevicePreviewScreenSize> = {
  desktop: { width: 1440, height: 900 },
  mobile: { width: 390, height: 844 },
}

/** Air kept around the frame, so it reads as a device and not as a cut-out. */
const FRAME_INSET_PX: number = 16

/** An unreachable host never fires `load`: past this delay the veil lifts anyway. */
const FRAME_LOAD_TIMEOUT_MS: number = 8_000

/** Pause after the last edit before it is pushed into the page, so typing does not flood it. */
const OVERRIDES_DEBOUNCE_MS: number = 200

/**
 * A published page in a real screen (laptop or phone) scaled to fit the pane, scrolling inside, told the unsaved
 * edits through the host's `_edit=1` mode: every message is posted as `{ type: 'dlh:preview', ...previewMessage }`.
 */
const props: AtelierDevicePreviewProps = defineProps({
  pageUrl: {
    type: String,
    required: true,
  },
  device: {
    type: String as PropType<TemplatePreviewDevice>,
    default: 'mobile',
  },
  previewMessage: {
    type: Object as PropType<Record<string, unknown> | null>,
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
  const separator: string = props.pageUrl.includes('?') ? '&' : '?'
  const nonce: string = props.reloadNonce ? `&_r=${props.reloadNonce}` : ''
  return `${props.pageUrl}${separator}_edit=1${nonce}`
})

/** Scale of the frame so the whole screen fits the pane, whichever side is tight. */
const frameScale: ComputedRef<number> = computed((): number => {
  if (paneWidth.value === 0 || paneHeight.value === 0) return 1
  const frame: AtelierDevicePreviewScreenSize = FRAME_SIZES[props.device ?? 'mobile']
  const widthScale: number = (paneWidth.value - FRAME_INSET_PX * 2) / frame.width
  const heightScale: number = (paneHeight.value - FRAME_INSET_PX * 2) / frame.height
  return Math.min(1, widthScale, heightScale)
})

/** The frame at its real size, scaled and centred in the pane. */
const frameStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const scale: number = frameScale.value
  const frame: AtelierDevicePreviewScreenSize = FRAME_SIZES[props.device ?? 'mobile']
  return {
    width: `${frame.width}px`,
    height: `${frame.height}px`,
    transform: `scale(${scale})`,
    left: `calc(50% - ${(frame.width * scale) / 2}px)`,
    top: `calc(50% - ${(frame.height * scale) / 2}px)`,
  }
})

/**
 * Push the unsaved edits into the page, which repaints at once.
 */
function postOverrides(): void {
  const frame: HTMLIFrameElement | null = frameElement.value
  if (!frame?.contentWindow || !props.previewMessage) return
  let origin: string
  try {
    origin = new URL(props.pageUrl).origin
  } catch {
    return
  }
  frame.contentWindow.postMessage({ type: 'dlh:preview', ...props.previewMessage }, origin)
}

/**
 * Debounced {@link postOverrides}, so typing a name or a colour does not flood the page.
 */
function scheduleOverrides(): void {
  if (messageTimer) clearTimeout(messageTimer)
  messageTimer = setTimeout(postOverrides, OVERRIDES_DEBOUNCE_MS)
}

/**
 * Cover the frame while the page loads, for a bounded time.
 */
function beginFrameLoad(): void {
  isLoading.value = true
  if (frameLoadTimeoutTimer) clearTimeout(frameLoadTimeoutTimer)
  frameLoadTimeoutTimer = setTimeout((): void => {
    isLoading.value = false
  }, FRAME_LOAD_TIMEOUT_MS)
}

/**
 * Lift the veil once the page is loaded and send it the unsaved edits again: a fresh load starts from the
 * published page, so edits made before it would be lost otherwise.
 */
function endFrameLoad(): void {
  if (frameLoadTimeoutTimer) clearTimeout(frameLoadTimeoutTimer)
  isLoading.value = false
  postOverrides()
}

watch((): Record<string, unknown> | null => props.previewMessage ?? null, scheduleOverrides, { deep: true })

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
