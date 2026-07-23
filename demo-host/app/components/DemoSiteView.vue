<template>
  <component :is="templateRoot" v-if="templateRoot && hasRenderableContent" :content="siteContent" />
</template>

<script lang="ts" setup>
import type { Component, ComputedRef, PropType, Ref } from 'vue'
// L'objet composant, jamais son nom : un nom en chaîne rend vide en prod sur un build vert.
import {
  LazyArtisanEditoRoot,
  LazyPlumberSignatureRoot,
  LazyPlumberAtelierRoot,
  LazyPlumberCuivreRoot,
  LazyElectricianLumenRoot,
  LazyMechanicPitlaneRoot,
  LazyDentalRoot,
  LazyFoodRoot,
  LazyBarberRoot,
} from '#components'
import {
  fetchStoryblokDraftContent,
  isStoryblokVisualEditor,
  useStoryblokBridge,
} from '~/composables/useStoryblokPreview'
import type { DemoSiteViewProps } from '~/types/DemoSiteView'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SiteContent } from '@devleadhunter/website-content'

/**
 * Defines the component props.
 */
const props: DemoSiteViewProps = defineProps({
  site: {
    type: Object as PropType<DemoSitePublic>,
    required: true,
  },
})

/** `Lazy*` roots keep each template in its own chunk, so a demo only downloads its own. */
const TEMPLATE_ROOTS: Record<string, Component> = {
  'artisan-edito': LazyArtisanEditoRoot,
  'plumber-signature': LazyPlumberSignatureRoot,
  'plumber-atelier': LazyPlumberAtelierRoot,
  'plumber-cuivre': LazyPlumberCuivreRoot,
  'electrician-lumen': LazyElectricianLumenRoot,
  'mechanic-pitlane': LazyMechanicPitlaneRoot,
  dental: LazyDentalRoot,
  food: LazyFoodRoot,
  barber: LazyBarberRoot,
}

const route = useRoute()
const { init: initDemoTracking } = useDemoTracking()

const isVisualEditor: ComputedRef<boolean> = computed((): boolean => isStoryblokVisualEditor(route.query))

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

const liveEditorContent: Ref<Record<string, unknown>> = ref({})

const resolvedContent: ComputedRef<Record<string, unknown>> = computed((): Record<string, unknown> => {
  if (Object.keys(liveEditorContent.value).length > 0) {
    return liveEditorContent.value
  }
  if (storyblokDraftContent.value) {
    return storyblokDraftContent.value
  }
  return (props.site.content_json as Record<string, unknown>) ?? {}
})

const isFlatSiteContent: ComputedRef<boolean> = computed(
  (): boolean => 'businessName' in resolvedContent.value && !('body' in resolvedContent.value),
)

const hasRenderableContent: ComputedRef<boolean> = computed(
  (): boolean => isFlatSiteContent.value || StoryblokSiteContentBridge.isStoryblokSiteContent(resolvedContent.value),
)

const templateRoot: ComputedRef<Component | null> = computed(
  (): Component | null => TEMPLATE_ROOTS[props.site.template_id] ?? null,
)

const siteContent: ComputedRef<SiteContent> = computed((): SiteContent => {
  if (isFlatSiteContent.value) {
    return resolvedContent.value as SiteContent
  }
  return StoryblokSiteContentBridge.toSiteContent(resolvedContent.value)
})

watch(storyblokDraftContent, (): void => {
  liveEditorContent.value = {}
})

useStoryblokBridge(isVisualEditor, (content: Record<string, unknown>): void => {
  liveEditorContent.value = content
})

onMounted((): void => {
  const variant: string | null = typeof route.query.v === 'string' ? route.query.v : null
  void initDemoTracking(props.site.slug, props.site.status, variant)
})
</script>
