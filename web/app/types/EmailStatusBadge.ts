import type { EmailStatus } from '~/types'

export type EmailStatusBadgeProps = {
  status: EmailStatus
}

export type EmailStatusPresentation = {
  label: string
  icon: string
  variant: string
  spin?: boolean
}
