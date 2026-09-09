<template>
  <div class="@container">
    <div
      :class="templatesBelowPreview ? 'flex flex-col-reverse gap-4' : 'grid gap-4 @3xl:grid-cols-[280px_minmax(0,1fr)]'"
    >
      <div
        :class="[
          'flex gap-2 overflow-x-auto pb-1',
          templatesBelowPreview
            ? ''
            : '@3xl:max-h-[560px] @3xl:flex-col @3xl:overflow-x-visible @3xl:overflow-y-auto @3xl:pr-1 @3xl:pb-0',
        ]"
      >
        <button
          v-for="template in sortedTemplates"
          :key="template.id"
          type="button"
          :class="[
            'w-56 shrink-0 rounded-xl border p-2 text-left transition-colors',
            templatesBelowPreview ? '' : '@3xl:w-full',
            modelValue === template.id
              ? 'border-[var(--app-ink)] bg-[var(--app-surface)] ring-1 ring-[var(--app-ink)]/15'
              : 'border-[var(--app-line)] bg-[var(--app-surface)] hover:border-[var(--app-ink-soft)]',
          ]"
          @click="selectTemplate(template)"
        >
          <div class="relative aspect-[16/10] overflow-hidden rounded-lg border border-[var(--app-line)]">
            <img
              v-if="!failedThumbnails.has(template.id)"
              :src="thumbnailUrl(template.id)"
              :alt="`Aperçu du template ${template.name}`"
              class="absolute inset-0 h-full w-full object-cover object-top"
              loading="lazy"
              @error="failedThumbnails.add(template.id)"
            />
            <div v-else class="absolute inset-0" :style="{ background: fallbackGradient(template) }"></div>
            <span
              v-if="modelValue === template.id"
              class="absolute top-1.5 right-1.5 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--app-ink)] text-[var(--app-bg)]"
            >
              <UIcon name="i-lucide-check" class="h-3 w-3" />
            </span>
          </div>
          <div class="mt-2 flex items-center justify-between gap-2 px-0.5 pb-0.5">
            <span class="truncate text-[13px] font-semibold text-[var(--app-ink)]">{{ template.name }}</span>
            <span
              v-if="isRecommended(template)"
              class="shrink-0 rounded-full bg-[var(--app-accent-soft)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
            >
              Recommandé
            </span>
          </div>
        </button>
      </div>

      <div v-if="selectedTemplate" :class="['app-card overflow-hidden', templatesBelowPreview ? '' : 'self-start']">
        <div
          ref="previewContainer"
          :class="[
            'relative aspect-[16/10] overflow-hidden border-b border-[var(--app-line)]',
            isLivePreview && previewDevice === 'mobile' ? 'bg-[var(--app-surface-2)]' : '',
          ]"
        >
          <template v-if="isLivePreview">
            <iframe
              ref="previewFrame"
              :src="livePreviewUrl"
              :class="[
                'absolute top-0 origin-top-left border-0 bg-white',
                previewDevice === 'mobile'
                  ? 'h-[844px] w-[390px] rounded-xl shadow-[var(--app-shadow-soft)]'
                  : 'left-0 h-[800px] w-[1280px]',
              ]"
              :style="liveFrameStyle"
              title="Aperçu interactif du template"
              @load="endPreviewLoad"
            />
          </template>
          <template v-else>
            <img
              v-if="!failedThumbnails.has(selectedTemplate.id)"
              :src="thumbnailUrl(selectedTemplate.id)"
              :alt="`Aperçu du template ${selectedTemplate.name}`"
              class="absolute inset-0 h-full w-full object-cover object-top"
            />
            <div v-else class="absolute inset-0" :style="{ background: fallbackGradient(selectedTemplate) }"></div>
          </template>

          <Transition name="preview-veil">
            <div
              v-if="isLivePreview && isPreviewLoading"
              class="absolute inset-0 flex flex-col items-center justify-center gap-3.5 bg-[var(--app-surface)]"
            >
              <div class="loader-smooth"></div>
              <span class="text-xs text-[var(--app-ink-soft)]">Chargement de l'aperçu…</span>
            </div>
          </Transition>

          <div
            v-if="isLivePreview"
            class="absolute top-3 right-3 flex overflow-hidden rounded-lg border border-[var(--app-line)] bg-[var(--app-surface)] shadow-[var(--app-shadow-soft)]"
          >
            <button
              type="button"
              title="Aperçu ordinateur"
              :class="deviceButtonClass('desktop')"
              @click="previewDevice = 'desktop'"
            >
              <UIcon name="i-lucide-monitor" class="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="Aperçu mobile"
              :class="deviceButtonClass('mobile')"
              @click="previewDevice = 'mobile'"
            >
              <UIcon name="i-lucide-smartphone" class="h-3.5 w-3.5" />
            </button>
          </div>

          <div class="absolute right-3 bottom-3 flex gap-2">
            <button
              type="button"
              class="app-btn-secondary h-8 px-3 text-xs shadow-[var(--app-shadow-soft)]"
              @click="toggleLivePreview"
            >
              <UIcon :name="isLivePreview ? 'i-lucide-image' : 'i-lucide-play'" class="h-3.5 w-3.5" />
              {{ isLivePreview ? 'Image' : 'Aperçu live' }}
            </button>
            <a
              :href="livePreviewUrl"
              target="_blank"
              rel="noopener"
              class="app-btn-secondary h-8 px-3 text-xs shadow-[var(--app-shadow-soft)]"
              title="Ouvrir l'aperçu dans un nouvel onglet"
            >
              <UIcon name="i-lucide-external-link" class="h-3.5 w-3.5" />
            </a>
          </div>
        </div>

        <div class="space-y-4 p-5">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <p class="font-semibold text-[var(--app-ink)]">{{ selectedTemplate.name }}</p>
              <span
                v-if="isRecommended(selectedTemplate)"
                class="rounded-full bg-[var(--app-accent-soft)] px-2 py-0.5 text-[10px] font-semibold text-[var(--app-accent-ink)]"
              >
                Recommandé pour {{ recommendedTrade }}
              </span>
            </div>
            <p class="mt-1.5 text-xs leading-relaxed text-[var(--app-ink-soft)]">{{ selectedTemplate.description }}</p>
          </div>

          <div v-if="showColors" class="border-t border-[var(--app-line-soft)] pt-4">
            <DemoSitesColorEditor
              :template="selectedTemplate"
              :theme="theme"
              :use-brand-color="useBrandColor"
              :brand-color="brandColor"
              @update:theme="onColorEditorTheme"
              @update:use-brand-color="emit('update:useBrandColor', $event)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import type {
  TemplatePickerEmits,
  TemplatePickerProps,
  TemplatePreviewDevice,
  TemplateThemeColorKey,
} from '~/types/TemplatePicker'
import type { ComputedRef, EmitFn, PropType, Ref } from 'vue'
import type { DemoSiteServiceCard, DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'
import { isTemplateRecommendedFor, sortTemplatesByRecommendation } from '~/utils/templateRecommendation'

/** Template picker: compact list, real screenshot, live iframe preview with theme colors applied. */
const props: TemplatePickerProps = defineProps({
  templates: {
    type: Array as PropType<DemoSiteTemplate[]>,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
  theme: {
    type: Object as PropType<DemoSiteTheme>,
    required: true,
  },
  recommendedTrade: {
    type: String as PropType<string | null>,
    default: null,
  },
  // When set, the live preview shows this site instead of the template catalog.
  publishedSiteUrl: {
    type: String as PropType<string | null>,
    default: null,
  },
  // Bump to force the published-site iframe to reload after a regeneration (URL itself is unchanged).
  reloadNonce: {
    type: Number,
    default: 0,
  },
  // When true, stack a full-width preview with the template strip below it (demo site page).
  templatesBelowPreview: {
    type: Boolean,
    default: false,
  },
  // Action colour source: logo (true) / template (false). Null → hide the Logo/Template picker (wizard).
  useBrandColor: {
    type: Boolean as PropType<boolean | null>,
    default: null,
  },
  // Colour extracted from the prospect logo, for the "Logo" pill (null = no usable logo colour).
  brandColor: {
    type: String as PropType<string | null>,
    default: null,
  },
  // Hide the colour editor (the demo-site page hosts it in its configuration tab instead).
  showColors: {
    type: Boolean,
    default: true,
  },
  // Candidate photo placement pushed live into the published-site preview (null = published placement).
  previewPhotos: {
    type: Array as PropType<string[] | null>,
    default: null,
  },
  // Candidate colours pushed live into the published-site preview (null = keep the published palette).
  previewTheme: {
    type: Object as PropType<DemoSiteTheme | null>,
    default: null,
  },
  // Candidate section cards pushed live into the published-site preview (null = keep the published cards).
  previewServices: {
    type: Array as PropType<DemoSiteServiceCard[] | null>,
    default: null,
  },
})

const emit: EmitFn<TemplatePickerEmits> = defineEmits<TemplatePickerEmits>()

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()

const colorKeys: TemplateThemeColorKey[] = ['primary', 'secondary', 'accent']

/** Native layout viewport the live iframe renders at, per device, before it is fitted to the pane. */
const LIVE_VIEWPORTS: Record<TemplatePreviewDevice, { width: number; height: number }> = {
  desktop: { width: 1280, height: 800 },
  mobile: { width: 390, height: 844 },
}

const previewContainer: Ref<HTMLElement | null> = ref(null)
/** Live preview iframe, targeted by the postMessage overrides in published-site mode. */
const previewFrame: Ref<HTMLIFrameElement | null> = ref(null)
const paneWidth: Ref<number> = ref(640)
const paneHeight: Ref<number> = ref(400)
const isLivePreview: Ref<boolean> = ref(true)
const previewDevice: Ref<TemplatePreviewDevice> = ref('desktop')
const livePreviewUrl: Ref<string> = ref('')
const isPreviewLoading: Ref<boolean> = ref(true)
const failedThumbnails: Ref<Set<string>> = ref(new Set())

/** ResizeObserver keeping the zoomed iframe in sync with the preview pane width. */
let previewResizeObserver: ResizeObserver | null = null
/** Timer debouncing live preview reloads while colors are edited. */
let livePreviewReloadTimer: ReturnType<typeof setTimeout> | null = null
/** Timer lifting the loading veil when the iframe never reports a load. */
let previewLoadTimeoutTimer: ReturnType<typeof setTimeout> | null = null
/** Timer debouncing the postMessage overrides pushed into the published-site preview. */
let previewMessageTimer: ReturnType<typeof setTimeout> | null = null

/** The template currently selected in the list. */
const selectedTemplate: ComputedRef<DemoSiteTemplate | null> = computed(
  (): DemoSiteTemplate | null =>
    props.templates.find((template: DemoSiteTemplate): boolean => template.id === props.modelValue) ?? null,
)

/** Templates with the ones recommended for the targeted trade bubbled to the top. */
const sortedTemplates: ComputedRef<DemoSiteTemplate[]> = computed((): DemoSiteTemplate[] =>
  sortTemplatesByRecommendation(props.templates, props.recommendedTrade ?? null),
)

/**
 * Fit of the live iframe into the pane: full width for desktop, height-fit and centered for mobile.
 *
 * Plain `transform: scale` only — a `zoom`-based supersampling pass (sharper on HiDPI) was tried and
 * reverted: `zoom` on an iframe resizes the INNER viewport on some Chromium versions, which flipped
 * the preview to a phone layout, over-zoomed and cropped. Faithful layout beats sharpness here.
 */
const liveFrameStyle: ComputedRef<Record<string, string>> = computed((): Record<string, string> => {
  const viewport: { width: number; height: number } = LIVE_VIEWPORTS[previewDevice.value]
  if (previewDevice.value === 'mobile') {
    const scale: number = paneHeight.value / viewport.height
    return {
      transform: `scale(${scale})`,
      left: `calc(50% - ${(viewport.width * scale) / 2}px)`,
    }
  }
  return { transform: `scale(${paneWidth.value / viewport.width})` }
})

/**
 * Whether a template targets the trade the picker recommends for.
 * @param template - Template to test.
 * @returns True when one of the template's trade keywords matches.
 */
function isRecommended(template: DemoSiteTemplate): boolean {
  return isTemplateRecommendedFor(template, props.recommendedTrade ?? null)
}

/**
 * Static screenshot path of a template (bundled with the app).
 * @param templateId - Template identifier.
 * @returns The public thumbnail URL.
 */
function thumbnailUrl(templateId: string): string {
  return `/templates/${templateId}.jpg`
}

/**
 * Gradient used when a template has no screenshot yet.
 * @param template - Template whose default theme feeds the gradient.
 * @returns A CSS gradient string.
 */
function fallbackGradient(template: DemoSiteTemplate): string {
  return `linear-gradient(135deg, ${template.default_theme.secondary} 0%, ${template.default_theme.primary} 100%)`
}

/**
 * Build the demo-host catalog URL for a template, with the current colors applied.
 * @param template - Template to preview.
 * @returns The catalog page URL.
 */
function buildLivePreviewUrl(template: DemoSiteTemplate): string {
  const base: string = String(config.public.demoHostBase).replace(/\/$/, '')
  const params: URLSearchParams = new URLSearchParams()
  for (const key of colorKeys) {
    const color: string = props.modelValue === template.id ? props.theme[key] : template.default_theme[key]
    params.set(key, color.replace('#', ''))
  }
  return `${base}/t/${template.id}?${params.toString()}`
}

/**
 * Point the live iframe at the selected template with the current colors.
 *
 * With a published site, `_edit=1` switches the demo-host page into live-edit mode: it then accepts
 * the postMessage overrides below, so the REAL generated site previews colour / photo / template
 * changes instantly — never the empty catalog render.
 */
function applyLivePreviewUrl(): void {
  if (props.publishedSiteUrl) {
    const separator: string = props.publishedSiteUrl.includes('?') ? '&' : '?'
    const nonce: string = props.reloadNonce ? `&_r=${props.reloadNonce}` : ''
    livePreviewUrl.value = `${props.publishedSiteUrl}${separator}_edit=1${nonce}`
    return
  }
  if (selectedTemplate.value) livePreviewUrl.value = buildLivePreviewUrl(selectedTemplate.value)
}

/**
 * Refresh the live iframe URL, debounced so hex typing doesn't reload on every keystroke.
 */
function scheduleLivePreviewReload(): void {
  if (livePreviewReloadTimer) clearTimeout(livePreviewReloadTimer)
  livePreviewReloadTimer = setTimeout(applyLivePreviewUrl, 600)
}

/**
 * Push the pending edits (template, colours, photo order) into the published-site iframe, which
 * applies them instantly — no reload, no regeneration.
 */
function postPreviewOverrides(): void {
  if (!props.publishedSiteUrl) return
  const frame: HTMLIFrameElement | null = previewFrame.value
  if (!frame?.contentWindow) return
  let origin: string
  try {
    origin = new URL(props.publishedSiteUrl).origin
  } catch {
    return
  }
  frame.contentWindow.postMessage(
    {
      type: 'dlh:preview',
      templateId: props.modelValue,
      // Only pending colours override the published palette — the local theme state may not
      // perfectly reconstruct it, and repainting an untouched site would be a lie.
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
 * Debounced {@link postPreviewOverrides}, so hex typing or drag reorders don't flood the iframe.
 */
function schedulePreviewMessage(): void {
  if (previewMessageTimer) clearTimeout(previewMessageTimer)
  previewMessageTimer = setTimeout(postPreviewOverrides, 200)
}

/**
 * Cover the preview until the iframe reports its document is ready.
 */
function beginPreviewLoad(): void {
  isPreviewLoading.value = true
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
  // An unreachable demo-host never fires load: never leave the veil spinning for good.
  previewLoadTimeoutTimer = setTimeout((): void => {
    isPreviewLoading.value = false
  }, 8000)
}

/**
 * Lift the loading veil once the iframe finished loading, and re-send any pending edits — a reload
 * (regeneration nonce, navigation) starts from the published state and would lose them otherwise.
 */
function endPreviewLoad(): void {
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
  isPreviewLoading.value = false
  postPreviewOverrides()
}

/**
 * Toggle between the static screenshot and the live iframe.
 */
function toggleLivePreview(): void {
  isLivePreview.value = !isLivePreview.value
}

/**
 * Classes of a device toggle button (active device highlighted).
 * @param device - The device the button switches to.
 * @returns Button classes.
 */
function deviceButtonClass(device: TemplatePreviewDevice): string {
  const base: string = 'flex h-8 w-9 cursor-pointer items-center justify-center transition-colors'
  if (previewDevice.value === device) {
    return `${base} bg-[var(--app-ink)] text-[var(--app-bg)]`
  }
  return `${base} text-[var(--app-ink-soft)] hover:text-[var(--app-ink)]`
}

/**
 * Select a template and sync its default theme. With a published site the parent page owns the
 * theme transition (restore the published colours when re-picking the live template), so the
 * defaults are only pushed for the catalog flows (wizard, edit form).
 * @param template - Template picked in the list.
 */
function selectTemplate(template: DemoSiteTemplate): void {
  emit('update:modelValue', template.id)
  if (!props.publishedSiteUrl) emit('update:theme', { ...template.default_theme })
}

/**
 * Relay a colour change from the editor pane and make sure the live preview shows it.
 * @param theme - The updated theme.
 */
function onColorEditorTheme(theme: DemoSiteTheme): void {
  emit('update:theme', theme)
  isLivePreview.value = true
}

watch(
  (): string => props.modelValue,
  (_value: string, previous: string | undefined): void => {
    isLivePreview.value = true
    // Published site + template switch: the iframe URL doesn't change (same site), the new
    // template is pushed via postMessage — reloading would only flash the veil for nothing.
    if (props.publishedSiteUrl && previous !== undefined) {
      schedulePreviewMessage()
      return
    }
    beginPreviewLoad()
    applyLivePreviewUrl()
  },
  { immediate: true },
)

watch(
  (): DemoSiteTheme => props.theme,
  (): void => {
    if (props.publishedSiteUrl) {
      schedulePreviewMessage()
      return
    }
    scheduleLivePreviewReload()
  },
  { deep: true },
)

watch((): string[] | null => props.previewPhotos ?? null, schedulePreviewMessage, { deep: true })

watch((): DemoSiteTheme | null => props.previewTheme ?? null, schedulePreviewMessage, { deep: true })

watch((): DemoSiteServiceCard[] | null => props.previewServices ?? null, schedulePreviewMessage, { deep: true })

watch((): string | null => props.publishedSiteUrl ?? null, applyLivePreviewUrl)

watch((): number => props.reloadNonce ?? 0, applyLivePreviewUrl)

watch([livePreviewUrl, isLivePreview], (): void => {
  if (isLivePreview.value) beginPreviewLoad()
})

// The detail pane mounts only once templates are loaded: follow the element, not onMounted.
watch(previewContainer, (element: HTMLElement | null): void => {
  previewResizeObserver?.disconnect()
  if (element) previewResizeObserver?.observe(element)
})

onMounted((): void => {
  previewResizeObserver = new ResizeObserver((entries: ResizeObserverEntry[]): void => {
    const rect: DOMRectReadOnly | undefined = entries[0]?.contentRect
    if (rect && rect.width > 0) {
      paneWidth.value = rect.width
      paneHeight.value = rect.height
    }
  })
  if (previewContainer.value) previewResizeObserver.observe(previewContainer.value)
})

onBeforeUnmount((): void => {
  previewResizeObserver?.disconnect()
  if (livePreviewReloadTimer) clearTimeout(livePreviewReloadTimer)
  if (previewLoadTimeoutTimer) clearTimeout(previewLoadTimeoutTimer)
  if (previewMessageTimer) clearTimeout(previewMessageTimer)
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
