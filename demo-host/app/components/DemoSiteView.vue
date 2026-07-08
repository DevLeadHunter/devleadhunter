<template>
  <!--
    Migrated templates render from their own extends'd layer (a typed SiteContent) as soon as
    the resolved content is a SiteContent (Phase 4b — flat content_json or Storyblok-native).
    Legacy demos, whose content_json is still the rich blok tree, fall back to the in-repo
    template until they expire (14-day TTL) — so nothing breaks during the transition.
  -->
  <component
    v-if="migratedRoot && isSiteContent"
    :is="migratedRoot"
    :content="resolvedSiteContent" />
  <component
    v-else
    :is="legacyComponent"
    :content="renderContent"
    :business-name="site.business_name" />
</template>

<script lang="ts" setup>
import type { Component, ComputedRef, PropType, Ref } from 'vue'
// Legacy in-repo templates — render OLD demos whose content_json is still the rich blok tree.
import DemoPlumberSimplePage from '~/components/templates/plumber-simple/index.vue'
import DemoPlumberAtelierPage from '~/components/templates/plumber-atelier/index.vue'
import DemoPlumberSignaturePage from '~/components/templates/plumber-signature/index.vue'
// Lazy: heavier templates don't weigh down the others' bundles.
const DemoElectricianLumenPage = defineAsyncComponent(() => import('~/components/templates/electrician-lumen/index.vue'))
const DemoPlumberCuivrePage = defineAsyncComponent(() => import('~/components/templates/plumber-cuivre/index.vue'))
import { fetchStoryblokDraftContent, isStoryblokVisualEditor, useStoryblokBridge } from '~/composables/useStoryblokPreview'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SiteContent } from '@devleadhunter/website-content'
// Migrated layer roots (one per extends'd template). `Lazy*` = async → code-split, so a demo
// only loads its own template's chunk. We resolve to component OBJECTS here: a runtime string
// name is NOT resolvable via `<component :is>` for Nuxt auto-imported components (they aren't
// registered globally), so passing the object is required — passing a string renders an empty
// literal element.
import {
  LazyPlumberSimpleRoot,
  LazyPlumberSignatureRoot,
  LazyPlumberAtelierRoot,
  LazyPlumberCuivreRoot,
  LazyElectricianLumenRoot,
} from '#components'

const props = defineProps({
  site: {
    type: Object as PropType<DemoSitePublic>,
    required: true,
  },
})

const route = useRoute()
const isVisualEditor: ComputedRef<boolean> = computed((): boolean => isStoryblokVisualEditor(route.query))

/** template_id → the extends'd layer root component (async → each renders as its own chunk). */
const MIGRATED_ROOTS: Record<string, Component> = {
  'plumber-simple': LazyPlumberSimpleRoot,
  'plumber-signature': LazyPlumberSignatureRoot,
  'plumber-atelier': LazyPlumberAtelierRoot,
  'plumber-cuivre': LazyPlumberCuivreRoot,
  'electrician-lumen': LazyElectricianLumenRoot,
}

/** template_id → legacy in-repo template, for OLD rich-content demos during the transition. */
const LEGACY_COMPONENTS: Record<string, Component> = {
  'plumber-simple': DemoPlumberSimplePage,
  'plumber-atelier': DemoPlumberAtelierPage,
  'plumber-signature': DemoPlumberSignaturePage,
  'plumber-cuivre': DemoPlumberCuivrePage,
  'electrician-lumen': DemoElectricianLumenPage,
}

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

/** True when the resolved content is a SiteContent — flat (Phase 4b) or Storyblok-native `site_content`. */
const isSiteContent: ComputedRef<boolean> = computed((): boolean => {
  const content: Record<string, unknown> = renderContent.value
  return ('businessName' in content && !('body' in content)) || isStoryblokSiteContent(content)
})

/** The extends'd root component for this template, or null when it isn't migrated yet. */
const migratedRoot: ComputedRef<Component | null> = computed(
  (): Component | null => MIGRATED_ROOTS[props.site.template_id] ?? null,
)

/** Resolve the SiteContent from either the flat shape (pass-through) or Storyblok-native (flatten). */
const resolvedSiteContent: ComputedRef<SiteContent> = computed((): SiteContent => {
  const content: Record<string, unknown> = renderContent.value
  if ('businessName' in content && !('body' in content)) {
    return content as SiteContent
  }
  return storyblokSiteContentToSiteContent(content)
})

/** Legacy in-repo template for old rich demos (fallback: historical plumber-simple). */
const legacyComponent: ComputedRef<Component> = computed(
  (): Component => LEGACY_COMPONENTS[props.site.template_id] ?? DemoPlumberSimplePage,
)

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
