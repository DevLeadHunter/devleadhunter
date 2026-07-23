import type { TemplateScore } from '~/services/emailHealthService'

/** One displayed group of template scores. */
export type TemplateScoreGroup = {
  key: 'initial' | 'follow_up'
  label: string
  items: TemplateScore[]
  showBest: boolean
}
