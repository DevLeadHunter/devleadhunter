export type TemplateSelectOption = {
  id: number
  name: string
  subject: string
}

export type TemplateSelectCreateButtonPosition = 'top' | 'bottom' | 'both'

export type TemplateSelectProps = {
  modelValue: number | null
  templates: TemplateSelectOption[]
  allowCreate?: boolean
  createButtonPosition?: TemplateSelectCreateButtonPosition
}
