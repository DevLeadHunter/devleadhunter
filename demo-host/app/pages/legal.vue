<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Chargement…
  </div>
  <div
    v-else-if="error || !site?.legal"
    class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300"
  >
    Site introuvable.
  </div>
  <SiteLegalPage v-else :legal-notice="site.legal" :business-name="site.business_name" site-href="/" />
</template>

<script lang="ts" setup>
import type { DemoSitePublic } from '~/types/demoSite'

const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
const host: string = useRequestURL().host

const {
  data: site,
  pending,
  error,
}: Awaited<ReturnType<typeof useAsyncData<DemoSitePublic | undefined>>> = await useAsyncData<DemoSitePublic>(
  () => `demo-site-domain-${host}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/by-domain`, {
      params: { host },
    })
  },
)
</script>
