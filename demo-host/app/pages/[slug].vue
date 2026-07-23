<template>
  <div v-if="pending" class="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
    Loading demo site…
  </div>
  <div v-else-if="error || !site" class="flex min-h-screen items-center justify-center bg-slate-950 text-red-300">
    Demo site not found or expired.
  </div>
  <main v-else class="min-h-screen bg-white text-slate-900">
    <DemoSiteView :site="site" />
  </main>
</template>

<script lang="ts" setup>
import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'

const route = useRoute()
const config = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const {
  data: site,
  pending,
  error,
} = await useAsyncData(
  () => `demo-site-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

useSeoMeta({
  title: () => site.value?.business_name ?? 'Demo site',
})
</script>
