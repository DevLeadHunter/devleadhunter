import type { AtelierDevicePreviewOption } from '~/types/AtelierDevicePreview'

/** The two ways of looking at a page in an atelier: in a phone, or on a computer screen. */
export const ATELIER_PREVIEW_DEVICES: AtelierDevicePreviewOption[] = [
  { key: 'mobile', label: 'Téléphone', icon: 'i-lucide-smartphone' },
  { key: 'desktop', label: 'Ordinateur', icon: 'i-lucide-monitor' },
]
