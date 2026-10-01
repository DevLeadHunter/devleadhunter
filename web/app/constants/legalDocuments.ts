import type { LegalDocumentLink } from '~/types/LandingLegalDocument'

export const LEGAL_DOCUMENTS: LegalDocumentLink[] = [
  { id: 'notice', path: '/legal', labelKey: 'legal.nav.notice' },
  { id: 'privacy', path: '/privacy', labelKey: 'legal.nav.privacy' },
  { id: 'terms', path: '/terms', labelKey: 'legal.nav.terms' },
]
