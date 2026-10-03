import type { ComputedRef } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SiteLegalPageData, SiteLegalPagePaths } from '~/types/SiteLegalPage'
import { SiteLegalLinkUtils } from '~/utils/SiteLegalLinkUtils'

/**
 * The site a legal page belongs to, read by its slug on a demo or by its host on a client's domain, with the paths
 * between its home and legal pages.
 * @returns The site, its loading state, its logo and the paths of its pages.
 */
export async function useSiteLegalPageData(): Promise<SiteLegalPageData> {
  const route: ReturnType<typeof useRoute> = useRoute()
  const config: ReturnType<typeof useRuntimeConfig> = useRuntimeConfig()
  const slug: string = String(route.params.slug ?? '')
  const host: string = useRequestURL().host

  const {
    data: site,
    pending,
    error,
  }: Awaited<ReturnType<typeof useAsyncData<DemoSitePublic | undefined>>> = await useAsyncData<DemoSitePublic>(
    slug ? `demo-site-${slug}` : `demo-site-domain-${host}`,
    async (): Promise<DemoSitePublic> => {
      if (slug) {
        return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/${slug}`)
      }
      return await $fetch<DemoSitePublic>(`${config.public.apiBase}/api/v1/demo-sites/public/by-domain`, {
        params: { host },
      })
    },
  )

  const isLoading: ComputedRef<boolean> = computed((): boolean => pending.value)

  const hasFailed: ComputedRef<boolean> = computed((): boolean => Boolean(error.value) || !site.value?.legal)

  const logoUrl: ComputedRef<string | null> = computed((): string | null => {
    const logo: unknown = site.value?.content_json?.logo
    return typeof logo === 'string' && logo.trim() ? logo.trim() : null
  })

  const pagePaths: ComputedRef<SiteLegalPagePaths> = computed((): SiteLegalPagePaths =>
    slug ? SiteLegalLinkUtils.demoPagePaths(slug, route.query) : SiteLegalLinkUtils.deliveredPagePaths(),
  )

  return { site, isLoading, hasFailed, logoUrl, pagePaths }
}
