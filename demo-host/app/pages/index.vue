<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Chargement…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Site introuvable.
  </div>
  <main v-else class="min-h-screen bg-white text-slate-900">
    <DemoSiteView :site="site" />
  </main>
</template>

<script lang="ts" setup>
import type { DemoSitePublic } from '~/types/demoSite'

// Sert un site vendu par son domaine client ; la racine demo.dibodev.fr n'est pas un site et 404.
const config = useRuntimeConfig()
const url = useRequestURL()
const host: string = url.host

const {
  data: site,
  pending,
  error,
} = await useAsyncData(
  () => `demo-site-domain-${host}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/by-domain`, {
      params: { host },
    })
  },
)

useSeoMeta({
  title: () => site.value?.business_name ?? 'Site',
})
</script>
