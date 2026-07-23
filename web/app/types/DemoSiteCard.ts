import type { DemoSite } from '~/services/demoSiteService'

export type DemoSiteCardProps = {
  site: DemoSite
}

export type DemoSiteCardEmits = {
  copy: [url: string]
  open: [url: string]
}
