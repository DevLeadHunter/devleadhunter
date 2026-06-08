export interface Theme { primary: string; secondary: string; accent: string }
export const defaultTheme: Theme = { primary: '#0284c7', secondary: '#0f172a', accent: '#f59e0b' }
export interface HeroBlock { component?: string; title?: string; subtitle?: string; phone?: string; cta_label?: string; badge?: string }
export interface TrustItem { value?: string; label?: string }
export interface TrustBlock { component?: string; items?: TrustItem[] }
export interface ServiceItem { label?: string; description?: string; icon?: string }
export interface ServicesBlock { component?: string; heading?: string; subheading?: string; items?: ServiceItem[] }
export interface WhyItem { label?: string }
export interface WhyUsBlock { component?: string; heading?: string; items?: WhyItem[] }
export interface ContactBlock { component?: string; heading?: string; subheading?: string; phone?: string; email?: string; city?: string }
