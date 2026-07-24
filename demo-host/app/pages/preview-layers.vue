<template>
  <div v-if="!site" class="flex min-h-screen items-center justify-center text-slate-500">
    Template inconnu : {{ templateId }}
  </div>
  <DemoSiteView v-else :site="site" />
</template>

<script lang="ts" setup>
// Harnais DEV uniquement : rejoue le chemin de prod sans l'API. Jamais servi en démo réelle.
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import previewLayers from '~/utils/previewLayers.json'

const DEFAULT_TEMPLATE_ID: string = 'plumber-signature'

/** Flat SiteContents produced by the API pipeline, bundled so they exist on both SSR and client. */
const PREVIEW_SITE_CONTENTS: Record<string, Record<string, unknown>> = previewLayers as Record<
  string,
  Record<string, unknown>
>

const route: ReturnType<typeof useRoute> = useRoute()

const templateId: ComputedRef<string> = computed((): string =>
  typeof route.query.t === 'string' ? route.query.t : DEFAULT_TEMPLATE_ID,
)

const businessNameOverride: ComputedRef<string> = computed((): string =>
  typeof route.query.business === 'string' ? route.query.business.trim() : '',
)

/** Fake DemoSitePublic in `draft` status, which keeps every tracking path disabled. */
const site: ComputedRef<DemoSitePublic | null> = computed((): DemoSitePublic | null => {
  const previewContent: Record<string, unknown> | undefined = PREVIEW_SITE_CONTENTS[templateId.value]
  if (!previewContent) {
    return null
  }
  const businessName: string = businessNameOverride.value || String(previewContent.businessName ?? 'Preview')
  return {
    slug: `preview-${templateId.value}`,
    business_name: businessName,
    template_id: templateId.value,
    content_json: businessNameOverride.value ? { ...previewContent, businessName } : previewContent,
    status: 'draft',
    storyblok_preview_token: null,
    storyblok_region: null,
  }
})
</script>
