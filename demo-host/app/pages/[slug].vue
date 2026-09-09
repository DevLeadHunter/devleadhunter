<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Loading demo site…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-slate-950 text-red-300">
    Demo site not found or expired.
  </div>
  <main v-else class="min-h-screen bg-white text-slate-900">
    <DemoSiteView :site="previewedSite ?? site" />
    <DemoCtaBanner :site="site" />
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import type { DemoPreviewOverrides, DemoPreviewServiceCard } from '~/composables/useDemoPreviewOverrides'
import type { DemoSitePublic } from '~/types/demoSite'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

/** Live-edit mode: the dashboard preview iframe adds `?_edit=1` and drives us via postMessage. */
const isLiveEditPreview: ComputedRef<boolean> = computed((): boolean => route.query._edit === '1')

const { overrides }: { overrides: Ref<DemoPreviewOverrides> } = useDemoPreviewOverrides(isLiveEditPreview)

const {
  data: site,
  pending,
  error,
}: Awaited<ReturnType<typeof useAsyncData<DemoSitePublic | undefined>>> = await useAsyncData<DemoSitePublic>(
  () => `demo-site-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

useSeoMeta({
  title: () => site.value?.business_name ?? 'Demo site',
})

/**
 * Re-derive food's gallery-seeded section photos from a reordered gallery, mirroring the API's
 * generation seeding (`_seed_photo_slots`): the about-collage sides and the featured-review photo
 * come from the real gallery, so a live reorder must move them too — not just the collage centre
 * (`aboutImage`). Food is the only template whose `images` map is photo-derived; the others use fixed
 * decorative section images that the order must never touch.
 * @param content - The live-preview content being assembled (mutated in place).
 * @param gallery - The reordered gallery URLs (the photos after hero and about).
 */
function reseedFoodSectionPhotos(content: Record<string, unknown>, gallery: string[]): void {
  const images: Record<string, string> = {}
  if (gallery[0]) images.aboutCollageLeft = gallery[0]
  if (gallery[1]) images.aboutCollageRight = gallery[1]
  if (gallery[2]) images.testimonial = gallery[2]
  content.images = images
}

/**
 * The published site with the dashboard's live-edit overrides merged in (template, palette,
 * photo order, curated section cards) — what an instant editor preview renders. Null outside
 * live-edit mode or before any override arrives, so the regular published rendering is untouched.
 */
const previewedSite: ComputedRef<DemoSitePublic | null> = computed((): DemoSitePublic | null => {
  const published: DemoSitePublic | null | undefined = site.value
  if (!published || !isLiveEditPreview.value) return null
  const { templateId, palette, photos, services }: DemoPreviewOverrides = overrides.value
  if (!templateId && !palette && !photos && !services) return null
  const content: Record<string, unknown> = { ...((published.content_json ?? {}) as Record<string, unknown>) }
  if (palette) {
    content.palette = { ...((content.palette as Record<string, unknown>) ?? {}), ...palette }
  }
  if (photos && photos.length > 0) {
    // Same slot mapping as generation: [0] → hero, [1] → about, [2:] → gallery.
    content.heroImage = photos[0] ?? ''
    content.aboutImage = photos[1] ?? ''
    const gallery: string[] = photos.slice(2)
    content.gallery = gallery.map((url: string): { url: string; alt: string } => ({ url, alt: '' }))
    if ((templateId ?? published.template_id) === 'food') {
      reseedFoodSectionPhotos(content, gallery)
    }
  }
  if (services && services.length > 0) {
    // The curated cards replace the generated section wholesale, exactly as the API does on save.
    content.services = services.map(
      (card: DemoPreviewServiceCard): { title: string; description: string; image: string } => ({ ...card }),
    )
  }
  return {
    ...published,
    template_id: templateId ?? published.template_id,
    content_json: content,
  }
})

/**
 * Choisit une couleur de texte lisible (blanc ou encre) sur un fond hex donné.
 * @param background Couleur de fond au format `#rrggbb`
 * @returns `#111111` sur fond clair, sinon `#ffffff`
 */
function readableTextColor(background: string): string {
  const hex: string = background.replace('#', '')
  if (hex.length !== 6) {
    return '#ffffff'
  }
  const r: number = parseInt(hex.slice(0, 2), 16)
  const g: number = parseInt(hex.slice(2, 4), 16)
  const b: number = parseInt(hex.slice(4, 6), 16)
  const luminance: number = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.6 ? '#111111' : '#ffffff'
}

/**
 * Favicon propre au site : le logo du prospect s'il existe, sinon une pastille
 * SVG « initiale + couleur de marque » — jamais le favicon placeholder générique.
 */
const faviconHref: ComputedRef<string> = computed((): string => {
  const content: Record<string, unknown> = (site.value?.content_json ?? {}) as Record<string, unknown>
  const logo: string = typeof content.logo === 'string' ? content.logo.trim() : ''
  if (logo) {
    return logo
  }
  const palette: Record<string, unknown> = (content.palette ?? {}) as Record<string, unknown>
  const background: string =
    typeof palette.primary === 'string' && palette.primary.trim() ? palette.primary.trim() : '#111111'
  const name: string = site.value?.business_name ?? ''
  const initial: string = (name.match(/[a-z0-9]/i)?.[0] ?? '●').toUpperCase()
  const svg: string =
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">` +
    `<rect width="64" height="64" rx="14" fill="${background}"/>` +
    `<text x="32" y="34" dominant-baseline="central" text-anchor="middle" ` +
    `font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="700" ` +
    `fill="${readableTextColor(background)}">${initial}</text></svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
})

useHead(() => ({
  link: [{ key: 'favicon', rel: 'icon', href: faviconHref.value }],
}))
</script>
