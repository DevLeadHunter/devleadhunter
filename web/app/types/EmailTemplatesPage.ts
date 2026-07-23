import type { EmailTemplate } from '~/types'

/** One displayed group of templates. */
export type TemplateGroup = {
  key: string
  heading: string
  templates: EmailTemplate[]
}
