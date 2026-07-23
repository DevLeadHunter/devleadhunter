import type { DemoSiteTemplate, DemoSiteTheme } from '~/services/demoSiteService'

export type TemplatePickerProps = {
  templates: DemoSiteTemplate[]
  modelValue: string
  theme: DemoSiteTheme
}

export type TemplateThemeColorKey = keyof DemoSiteTheme
