<template>
  <!-- plumber-cuivre renders from its own extends'd layer (typed SiteContent). -->
  <PlumberCuivreRoot
    v-if="isCuivreTemplate"
    :content="cuivreSiteContent" />
  <component
    v-else
    :is="templateComponent"
    :content="renderContent"
    :business-name="site.business_name" />
</template>

<script lang="ts" setup>
import type { Component, ComputedRef, PropType, Ref } from 'vue'
// Chaque template est isolée dans son dossier — imports directs (pas d'auto-import par nom).
import DemoPlumberSimplePage from '~/components/templates/plumber-simple/index.vue'
import DemoPlumberAtelierPage from '~/components/templates/plumber-atelier/index.vue'
import DemoPlumberSignaturePage from '~/components/templates/plumber-signature/index.vue'

// Templates chargées en lazy : leur code (GSAP inclus pour Lumen) n'alourdit pas les démos des autres templates.
const DemoElectricianLumenPage = defineAsyncComponent(() => import('~/components/templates/electrician-lumen/index.vue'))
// plumber-cuivre is now served from its own repo as a Nuxt layer (extends) → PlumberCuivreRoot.
import { fetchStoryblokDraftContent, isStoryblokVisualEditor, useStoryblokBridge } from '~/composables/useStoryblokPreview'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SiteContent } from '@devleadhunter/website-content'

const props = defineProps({
  site: {
    type: Object as PropType<DemoSitePublic>,
    required: true,
  },
})

const route = useRoute()
const isVisualEditor: ComputedRef<boolean> = computed((): boolean => isStoryblokVisualEditor(route.query))

/** Map template_id → composant de rendu (fallback : plumber-simple historique). */
const TEMPLATE_COMPONENTS: Record<string, Component> = {
  'plumber-simple': DemoPlumberSimplePage,
  'plumber-atelier': DemoPlumberAtelierPage,
  'plumber-signature': DemoPlumberSignaturePage,
  'electrician-lumen': DemoElectricianLumenPage,
}
const templateComponent: ComputedRef<Component> = computed(
  (): Component => TEMPLATE_COMPONENTS[props.site.template_id] ?? DemoPlumberSimplePage,
)

const { data: storyblokDraftContent } = useAsyncData(
  () => `storyblok-draft-${props.site.slug}-${isVisualEditor.value}`,
  async (): Promise<Record<string, unknown> | null> => {
    if (!isVisualEditor.value || !props.site.storyblok_preview_token) {
      return null
    }
    return await fetchStoryblokDraftContent(props.site.storyblok_preview_token, props.site.storyblok_region)
  },
  { watch: [isVisualEditor] },
)

const liveContent: Ref<Record<string, unknown>> = ref({})

const renderContent: ComputedRef<Record<string, unknown>> = computed((): Record<string, unknown> => {
  if (Object.keys(liveContent.value).length > 0) {
    return liveContent.value
  }
  if (storyblokDraftContent.value) {
    return storyblokDraftContent.value
  }
  return (props.site.content_json as Record<string, unknown>) ?? {}
})

/** plumber-cuivre is rendered by its extends'd layer (PlumberCuivreRoot), fed a typed SiteContent. */
const isCuivreTemplate: ComputedRef<boolean> = computed(
  (): boolean => props.site.template_id === 'plumber-cuivre',
)
/**
 * Resolve the SiteContent for the plumber-cuivre layer from whichever of three shapes
 * `renderContent` currently is:
 * 1. flat SiteContent (Phase 4b content_json) — `businessName` present, no `body` → pass through.
 * 2. Storyblok-native `site_content` (Visual Editor / preview draft) → flatten via the bridge.
 * 3. legacy rich `cuivre_*` bloks (old demos' content_json / Storyblok) → the historical bridge.
 */
const cuivreSiteContent: ComputedRef<SiteContent> = computed((): SiteContent => {
  const content: Record<string, unknown> = renderContent.value
  if ('businessName' in content && !('body' in content)) {
    return content as SiteContent
  }
  if (isStoryblokSiteContent(content)) {
    return storyblokSiteContentToSiteContent(content)
  }
  return richCuivreToSiteContent(content, props.site.business_name)
})

watch(storyblokDraftContent, (): void => {
  liveContent.value = {}
})

useStoryblokBridge(isVisualEditor, (content: Record<string, unknown>): void => {
  liveContent.value = content
})

// Behavioural tracking — only for live demos (status='active'); never on a delivered site.
const { init: initDemoTracking } = useDemoTracking()
onMounted((): void => {
  const variant: string | null = typeof route.query.v === 'string' ? route.query.v : null
  void initDemoTracking(props.site.slug, props.site.status, variant)
})
</script>
