export type DemoSiteStatTone = 'success' | 'warning' | 'muted' | undefined

export type DemoSiteStat = {
  label: string
  value: string
  tone: DemoSiteStatTone
}
