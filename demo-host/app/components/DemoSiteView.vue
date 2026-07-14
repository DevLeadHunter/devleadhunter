<template>
  <!--
    Each template renders from its own extends'd layer (a typed SiteContent). demo-host resolves
    the content (flat content_json or Storyblok-native `site_content`) to a SiteContent and passes
    it to the layer root. The legacy in-repo templates were removed once the migration completed.
  -->
  <component
    v-if="migratedRoot && isSiteContent"
    :is="migratedRoot"
    :content="resolvedSiteContent" />
</template>

<script lang="ts" setup>
import type { Component, ComputedRef, PropType, Ref } from 'vue'
// Migrated layer roots (one per extends'd template). `Lazy*` = async → code-split, so a demo
// only loads its own template's chunk. We pass the component OBJECT (not a string name): a
// runtime string name isn't resolvable via `<component :is>` for Nuxt auto-imported components.
import {
  LazyArtisanEditoRoot,
  LazyPlumberSignatureRoot,
  LazyPlumberAtelierRoot,
  LazyPlumberCuivreRoot,
  LazyElectricianLumenRoot,
  LazyMechanicPitlaneRoot,
  LazyDentalRoot,
  LazyFoodRoot,
} from '#components'
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

/** template_id → the extends'd layer root component (async → each renders as its own chunk). */
const MIGRATED_ROOTS: Record<string, Component> = {
  'artisan-edito': LazyArtisanEditoRoot,
  'plumber-signature': LazyPlumberSignatureRoot,
  'plumber-atelier': LazyPlumberAtelierRoot,
  'plumber-cuivre': LazyPlumberCuivreRoot,
  'electrician-lumen': LazyElectricianLumenRoot,
  'mechanic-pitlane': LazyMechanicPitlaneRoot,
  dental: LazyDentalRoot,
  food: LazyFoodRoot,
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

/** True when the resolved content is a SiteContent — flat (content_json) or Storyblok-native `site_content`. */
const isSiteContent: ComputedRef<boolean> = computed((): boolean => {
  const content: Record<string, unknown> = renderContent.value
  return ('businessName' in content && !('body' in content)) || isStoryblokSiteContent(content)
})

/** The extends'd root component for this template, or null for an unknown template_id. */
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
