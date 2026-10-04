export type TemplateSelectOption = {
  id: number
  name: string
  subject: string
  is_active: boolean
}

/** Menu entry of the searchable picker: a template flattened for USelectMenu. */
export type TemplateSelectItem = {
  value: number
  label: string
  description: string
}

export type TemplateSelectProps = {
  modelValue: number | null
  templates: TemplateSelectOption[]
  allowCreate?: boolean
}

export type TemplateSelectEmits = {
  /** New selection; `0` means none. */
  'update:modelValue': [value: number]
  create: []
  preview: [templateId: number]
}
