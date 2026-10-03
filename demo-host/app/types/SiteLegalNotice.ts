export type SiteLegalLine = {
  label: string | null
  text: string
  href: string | null
}

export type SiteLegalBlockKind = 'identity' | 'text'

export type SiteLegalBlock = {
  heading: string
  kind: SiteLegalBlockKind
  lines: SiteLegalLine[]
}

export type SiteLegalSection = {
  anchor: string
  title: string
  blocks: SiteLegalBlock[]
}

export type SiteLegalLink = {
  label: string
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
