import type { CampaignChannelWords } from '~/types/CampaignChannelWords'
import type { CampaignResultsDay, CampaignResultsVisitMarks } from '~/types/CampaignResults'

export type CampaignResultsDailyChartProps = {
  days: CampaignResultsDay[]
  prospectNames: Record<number, string>
  marks: CampaignResultsVisitMarks
  isVisitTrackingAvailable: boolean
  periodLabel: string
  words: CampaignChannelWords
}

export type CampaignResultsDailyChartDisplayMode = 'chart' | 'table'

export type CampaignResultsDailyChartGeometry = {
  width: number
  height: number
  isNarrow: boolean
  left: number
  right: number
  top: number
  plotHeight: number
  plotBottom: number
  stripBottom: number
  bandWidth: number
}

export type CampaignResultsDailyChartVisitScale = {
  maximum: number
  ticks: number[]
}

export type CampaignResultsDailyChartBand = {
  key: string
  x: number
  width: number
  isLabelled: boolean
}

export type CampaignResultsDailyChartReplyPill = {
  key: string
  x: number
  width: number
  label: string
  replyCount: number
  markerXs: number[]
}

export type CampaignResultsDailyChartMailKind = 'firstMails' | 'followUps' | 'planned'

export type CampaignResultsDailyChartMailPart = {
  kind: CampaignResultsDailyChartMailKind
  count: number
}

export type CampaignResultsDailyChartMailSegment = {
  key: string
  kind: CampaignResultsDailyChartMailKind
  x: number
  y: number
  width: number
  height: number
  isTop: boolean
}

export type CampaignResultsDailyChartMailLabel = {
  key: string
  x: number
  y: number
  text: string
  isPlannedOnly: boolean
}

export type CampaignResultsDailyChartDayLabel = {
  key: string
  x: number
  text: string
  isToday: boolean
}

export type CampaignResultsDailyChartPeak = {
  x: number
  y: number
  label: string
  isLabelBefore: boolean
  isLabelled: boolean
}

export type CampaignResultsDailyChartMark = {
  key: string
  label: string
  value: string
  suffix: string
}

export type CampaignResultsDailyChartTooltipSwatch = 'visits' | 'firstMails' | 'followUps'

export type CampaignResultsDailyChartTooltipRow = {
  key: string
  swatch: CampaignResultsDailyChartTooltipSwatch | null
  label: string
  value: string
  isDetail: boolean
}
