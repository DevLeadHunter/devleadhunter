import type { Prospect } from '~/types'

export type ScrapingJobLivePanelProps = {
  logs: string[]
  prospects: Prospect[]
  isRunning: boolean
}
