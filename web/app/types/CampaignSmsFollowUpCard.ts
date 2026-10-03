import type { SmsTemplate, SmsTemplateModule } from '~/services/smsService'

export type CampaignSmsFollowUpCardProps = {
  templates: SmsTemplate[]
  campaignModule: SmsTemplateModule
  previewProspectId: number | null
  defaultDelayDays: number
}
