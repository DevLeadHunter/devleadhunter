import type { ComputedRef, Ref } from 'vue'
import type { DemoSitePublic } from '~/types/demoSite'
import type { SchemaOrgLocalBusiness } from '~/types/SiteStructuredData'
import { SiteStructuredDataUtils } from '~/utils/SiteStructuredDataUtils'

const STRUCTURED_DATA_KEY: string = 'site-structured-data'

/**
 * Describe a demo's or a sold site's business to Google and AI assistants in schema.org JSON-LD.
 * @param site - The site's public payload, empty while it loads or when it is not found.
 */
export function useSiteStructuredData(site: Ref<DemoSitePublic | undefined>): void {
  const route: ReturnType<typeof useRoute> = useRoute()
  const origin: string = useRequestURL().origin

  const homeUrl: ComputedRef<string> = computed((): string => {
    const slug: string = String(route.params.slug ?? '')
    return slug ? `${origin}/${encodeURIComponent(slug)}` : `${origin}/`
  })

  const localBusiness: ComputedRef<SchemaOrgLocalBusiness | null> = computed((): SchemaOrgLocalBusiness | null =>
    site.value ? SiteStructuredDataUtils.buildLocalBusiness(site.value, homeUrl.value) : null,
  )

  useHead(() => ({
    script: localBusiness.value
      ? [{ key: STRUCTURED_DATA_KEY, type: 'application/ld+json', innerHTML: localBusiness.value }]
      : [],
  }))
}
