<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Loading demo site…
  </div>
  <div
    v-else-if="error || !site?.legal"
    class="flex min-h-screen items-center justify-center bg-slate-950 text-red-300"
  >
    Demo site not found or expired.
  </div>
  <SiteLegalPage v-else :legal-notice="site.legal" :business-name="site.business_name" :site-href="siteHref" />
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import { SiteLegalLinkUtils } from '~/utils/SiteLegalLinkUtils'

const route: ReturnType<typeof useRoute> = useRoute()
const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

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

const siteHref: ComputedRef<string> = computed((): string => SiteLegalLinkUtils.demoHomePath(slug.value, route.query))
</script>
