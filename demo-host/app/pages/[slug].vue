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
import type { ComputedRef } from 'vue'

type DemoSitePublic = {
  slug: string
  business_name: string
  template_id: string
  content_json?: Record<string, unknown> | null
  status: string
}

const route = useRoute()
const config = useRuntimeConfig()
const slug: ComputedRef<string> = computed((): string => String(route.params.slug ?? ''))

const { data: site, pending, error } = await useAsyncData(
  () => `demo-site-${slug.value}`,
  async (): Promise<DemoSitePublic> => {
    return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug.value}`)
  },
  { watch: [slug] },
)

const renderContent: ComputedRef<Record<string, unknown>> = computed((): Record<string, unknown> => {
  return (site.value?.content_json as Record<string, unknown>) ?? {}
})

useSeoMeta({
  title: () => site.value?.business_name ?? 'Demo site',
})
</script>
