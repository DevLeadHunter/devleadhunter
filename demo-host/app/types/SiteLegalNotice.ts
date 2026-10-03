export type SiteLegalLine = {
  label: string | null
  text: string
  href: string | null
  paragraph: number
}

export type SiteLegalBlockKind = 'identity' | 'text'

export type SiteLegalPageKind = 'legal' | 'privacy'

export type SiteLegalBlock = {
  heading: string
  kind: SiteLegalBlockKind
  intro: string | null
  lines: SiteLegalLine[]
}

export type SiteLegalSection = {
  page: SiteLegalPageKind
  anchor: string
  title: string
  intro: string
  blocks: SiteLegalBlock[]
}

export type SiteLegalLink = {
  label: string
  page: SiteLegalPageKind
  anchor: string
}

export type SiteLegalNotice = {
  locale: string
  page_title: string
  accent_color: string | null
  demo_notice: string | null
  links: SiteLegalLink[]
  sections: SiteLegalSection[]
}
