import type { CampaignForecastItem } from '~/services/campaignService'

/** Live pointer-drag of a planned SMS row towards a forecast drop target (day pill / next week). */
export type ForecastSmsDragSession = {
  item: CampaignForecastItem
  rowElement: HTMLElement
  pointerId: number
  startClientX: number
  startClientY: number
  grabOffsetX: number
  grabOffsetY: number
  ghost: HTMLElement | null
  isActive: boolean
}
