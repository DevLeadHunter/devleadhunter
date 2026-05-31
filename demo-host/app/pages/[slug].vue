<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Loading demo site…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-slate-950 text-red-300">
    Demo site not found or expired.
  </div>
  <main v-else class="min-h-screen bg-white text-slate-900">
    <DemoPlumberSimplePage :content="renderContent" :business-name="site.business_name" />
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef, Ref } from 'vue'
import {
  fetchStoryblokDraftContent,
  isStoryblokVisualEditor,
  useStoryblokBridge,
} from '~/composables/useStoryblokPreview'

type DemoSitePublic = {
  slug: string
  business_name: string
  template_id: string
  storyblok_preview_token?: string | null
  storyblok_region?: string | null
  content_json?: Record<string, unknown> | null
  status: string
}

const route = useRoute()
const config = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))
const isVisualEditor: ComputedRef<boolean> = computed((): boolean => isStoryblokVisualEditor(route.query))

const { data: site, pending, error } = await useAsyncData(
  () => `demo-site-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

const { data: storyblokDraftContent } = await useAsyncData(
  () => `storyblok-draft-${slug.value}-${isVisualEditor.value}`,
  async (): Promise<Record<string, unknown> | null> => {
    if (!isVisualEditor.value || !site.value?.storyblok_preview_token) {
      return null
    }

    return await fetchStoryblokDraftContent(
      site.value.storyblok_preview_token,
      site.value.storyblok_region,
    )
  },
  { watch: [slug, isVisualEditor, site] },
)

const liveContent: Ref<Record<string, unknown>> = ref({})

const renderContent: ComputedRef<Record<string, unknown>> = computed((): Record<string, unknown> => {
  if (Object.keys(liveContent.value).length > 0) {
    return liveContent.value
  }
  if (storyblokDraftContent.value) {
    return storyblokDraftContent.value
  }
  return (site.value?.content_json as Record<string, unknown>) ?? {}
})

watch(
  [storyblokDraftContent, site],
  (): void => {
    liveContent.value = {}
  },
)

useStoryblokBridge(isVisualEditor, (content: Record<string, unknown>): void => {
  liveContent.value = content
})

useSeoMeta({
  title: () => site.value?.business_name ?? 'Demo site',
})
</script>
