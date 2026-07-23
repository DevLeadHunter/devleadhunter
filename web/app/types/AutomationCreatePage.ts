import type { AutomationMode } from '~/types/Automation'
import type { DemoSiteTheme } from '~/services/demoSiteService'

export type AutomationRecapRow = {
  label: string
  value: string
}

export type TunnelForm = {
  name: string
  mode: AutomationMode
  templateId: string
  theme: DemoSiteTheme
  autoCampaign: boolean
  emailA: number
  emailB: number
  metiers: string
  villes: string
  targetDays: number
  onlyWithoutWebsite: boolean
}
