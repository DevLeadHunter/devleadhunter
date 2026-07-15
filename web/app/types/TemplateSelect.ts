/**
 * A selectable email template option.
 */
export interface TemplateSelectOption {
  id: number
  name: string
  subject: string
}

/**
 * Props for the UiTemplateSelect component.
 */
export interface TemplateSelectProps {
  /** Selected template ID (``null`` or ``0`` means none selected). */
  modelValue: number | null
  /** Available templates to choose from. */
  templates: TemplateSelectOption[]
}
