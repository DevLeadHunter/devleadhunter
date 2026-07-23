import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

export type TemplatePickerProps = {
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
}

export type TemplateThemeColorKey = keyof DemoSiteTheme

export type TemplatePickerEmits = {
  'update:modelValue': [value: string]
  'update:theme': [value: DemoSiteTheme]
}
